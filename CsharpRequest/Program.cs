using Microsoft.EntityFrameworkCore;
using Microsoft.OpenApi.Models;
using PurchaseRequestsService.Infrastructure;
using PurchaseRequestsService.Integrations;
using PurchaseRequestsService.Data;
using PurchaseRequestsService.Models;
using PurchaseRequestsService.Transport;

var builder = WebApplication.CreateBuilder(args);

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection") ?? "Data Source=app.db";

var urls = builder.Configuration.GetSection("Urls").Get<string[]>() ?? Array.Empty<string>();
if (urls.Length > 0)
{
    builder.WebHost.UseUrls(urls);
}

builder.Services.AddDbContext<PurchaseRequestContext>(options =>
    options.UseSqlite(connectionString));

builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo
    {
        Title = "Purchase Requests Service",
        Version = "v1",
        Description = "API para cadastro, consulta e aprovação de solicitações de compra."
    });
});

builder.Services.Configure<ConsulOptions>(builder.Configuration.GetSection("Consul"));
builder.Services.AddHostedService<ConsulRegistrationHostedService>();

builder.Services.Configure<CapitaliaOptions>(builder.Configuration.GetSection("Capitalia"));
builder.Services.AddHttpClient<CapitaliaApprovalClient>((serviceProvider, client) =>
{
    var options = serviceProvider.GetRequiredService<Microsoft.Extensions.Options.IOptions<CapitaliaOptions>>().Value;
    if (!string.IsNullOrWhiteSpace(options.BaseAddress))
    {
        client.BaseAddress = new Uri(options.BaseAddress, UriKind.Absolute);
    }
    client.Timeout = TimeSpan.FromSeconds(30);
});

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<PurchaseRequestContext>();
    db.Database.EnsureCreated();
}

if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

var getCatalogItemsHandler = async (PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var items = await db.PurchaseItems
        .Where(item => item.Active)
        .OrderBy(item => item.Name)
        .ToListAsync(cancellationToken);

    return Results.Ok(items);
};

var getCatalogItemByIdHandler = async (int id, PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var item = await db.PurchaseItems
        .Where(i => i.Active)
        .FirstOrDefaultAsync(i => i.Id == id, cancellationToken);

    return item is null
        ? Results.NotFound(new { message = $"Item {id} not found" })
        : Results.Ok(item);
};

var createPurchaseRequestHandler = async (CreatePurchaseRequestDto dto, PurchaseRequestContext db, ILogger<Program> logger, CancellationToken cancellationToken) =>
{
    try
    {
        var requesterName = dto.RequesterName?.Trim();
        var department = dto.Department?.Trim() ?? string.Empty;

        if (string.IsNullOrWhiteSpace(requesterName))
        {
            return Results.BadRequest(new { message = "Informe o nome do solicitante." });
        }

        if (dto.Items is null || dto.Items.Count == 0)
        {
            return Results.BadRequest(new { message = "A solicitação precisa conter ao menos um item." });
        }

        var normalizedLines = dto.Items
            .Where(line => line.ItemId > 0 && line.Quantity > 0)
            .ToList();

        if (normalizedLines.Count == 0)
        {
            return Results.BadRequest(new { message = "Informe itens válidos com quantidades maiores que zero." });
        }

        var itemIds = normalizedLines.Select(line => line.ItemId).Distinct().ToList();

        var catalogItems = await db.PurchaseItems
            .Where(item => itemIds.Contains(item.Id) && item.Active)
            .ToDictionaryAsync(item => item.Id, cancellationToken);

        var missingItems = itemIds.Where(id => !catalogItems.ContainsKey(id)).ToList();
        if (missingItems.Count > 0)
        {
            return Results.NotFound(new
            {
                message = "Um ou mais itens informados não existem no catálogo.",
                missingItems
            });
        }

        var request = new PurchaseRequest
        {
            RequesterName = requesterName,
            Department = department,
            RequestedAt = DateTime.UtcNow,
            Status = RequestStatus.Pending
        };

        foreach (var line in normalizedLines)
        {
            var item = catalogItems[line.ItemId];
            var unitPrice = item.UnitPrice;
            var quantity = line.Quantity;

            request.Lines.Add(new PurchaseRequestLine
            {
                PurchaseItemId = item.Id,
                Quantity = quantity,
                UnitPrice = unitPrice,
                LineTotal = unitPrice * quantity
            });
        }

        request.TotalValue = request.Lines.Sum(line => line.LineTotal);

        db.PurchaseRequests.Add(request);
        await db.SaveChangesAsync(cancellationToken);

        logger.LogInformation(
            "Solicitação de compra {RequestId} criada com sucesso para {Requester}",
            request.Id,
            requesterName);

        var created = await db.PurchaseRequests
            .Include(r => r.Lines)
            .ThenInclude(line => line.PurchaseItem)
            .FirstAsync(r => r.Id == request.Id, cancellationToken);

        return Results.Created($"/requests/{created.Id}", new
        {
            message = "Solicitação de compra criada com sucesso.",
            request = created.ToResponse()
        });
    }
    catch (Exception ex)
    {
        logger.LogError(ex, "Erro ao registrar solicitação de compra");
        return Results.Problem(
            title: "Erro interno",
            detail: "Não foi possível registrar a solicitação neste momento.",
            statusCode: StatusCodes.Status500InternalServerError);
    }
};

var getPurchaseRequestsHandler = async (PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var requests = await db.PurchaseRequests
        .Include(r => r.Lines)
        .ThenInclude(line => line.PurchaseItem)
        .OrderByDescending(r => r.RequestedAt)
        .ToListAsync(cancellationToken);

    return Results.Ok(requests.Select(r => r.ToResponse()));
};

var getPurchaseRequestByIdHandler = async (Guid id, PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var request = await db.PurchaseRequests
        .Include(r => r.Lines)
        .ThenInclude(line => line.PurchaseItem)
        .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);

    return request is null
        ? Results.NotFound(new { message = $"Request {id} not found" })
        : Results.Ok(request.ToResponse());
};

var getPurchaseRequestItemHandler = async (Guid requestId, int itemId, PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var line = await db.PurchaseRequestLines
        .Include(l => l.PurchaseItem)
        .FirstOrDefaultAsync(l => l.PurchaseRequestId == requestId && l.PurchaseItemId == itemId, cancellationToken);

    return line is null
        ? Results.NotFound(new { message = $"Item {itemId} is not associated with request {requestId}" })
        : Results.Ok(line.ToResponse());
};

var confirmPurchaseRequestHandler = async (Guid id, PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var request = await db.PurchaseRequests
        .Include(r => r.Lines)
        .ThenInclude(line => line.PurchaseItem)
        .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);

    if (request is null)
    {
        return Results.NotFound(new { message = $"Request {id} not found" });
    }

    if (request.Status == RequestStatus.Rejected)
    {
        return Results.BadRequest(new { message = "Rejected requests cannot be confirmed." });
    }

    request.Status = RequestStatus.Confirmed;
    await db.SaveChangesAsync(cancellationToken);

    return Results.Ok(new
    {
        message = "Solicitação confirmada com sucesso.",
        request = request.ToResponse()
    });
};

var submitForExternalApprovalHandler = async (Guid id, PurchaseRequestContext db, CapitaliaApprovalClient capitaliaClient, CancellationToken cancellationToken) =>
{
    if (!capitaliaClient.IsEnabled)
    {
        return Results.Problem(
            title: "Integração desabilitada",
            detail: "Configure a seção Capitalia no appsettings.json para habilitar a aprovação automática.",
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }

    var request = await db.PurchaseRequests
        .Include(r => r.Lines)
        .ThenInclude(line => line.PurchaseItem)
        .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);

    if (request is null)
    {
        return Results.NotFound(new { message = $"Request {id} not found" });
    }

    var approval = await capitaliaClient.RequestApprovalAsync(request, cancellationToken);
    if (approval is null)
    {
        return Results.Problem(
            title: "Falha na integração com Capitalia",
            detail: "Não foi possível obter uma decisão externa. Verifique a disponibilidade do serviço Python.",
            statusCode: StatusCodes.Status502BadGateway);
    }

    request.ExternalDecision = approval.Decision;
    request.ExternalDecisionNotes = approval.Notes;
    request.ExternalDecisionAt = DateTime.UtcNow;
    request.Status = approval.Approved ? RequestStatus.Confirmed : RequestStatus.Rejected;

    await db.SaveChangesAsync(cancellationToken);

    return Results.Ok(new
    {
        message = "Solicitação avaliada com sucesso pelo serviço externo.",
        request = request.ToResponse(),
        approval
    });
};

var rejectPurchaseRequestHandler = async (Guid id, PurchaseRequestContext db, CancellationToken cancellationToken) =>
{
    var request = await db.PurchaseRequests
        .Include(r => r.Lines)
        .ThenInclude(line => line.PurchaseItem)
        .FirstOrDefaultAsync(r => r.Id == id, cancellationToken);

    if (request is null)
    {
        return Results.NotFound(new { message = $"Request {id} not found" });
    }

    if (request.Status == RequestStatus.Confirmed)
    {
        return Results.BadRequest(new { message = "Confirmed requests cannot be rejected." });
    }

    request.Status = RequestStatus.Rejected;
    await db.SaveChangesAsync(cancellationToken);

    return Results.Ok(new
    {
        message = "Solicitação rejeitada com sucesso.",
        request = request.ToResponse()
    });
};

var requests = app.MapGroup("/requests");

app.MapGet("/", () => Results.Ok(new { message = "Purchase Requests Service running" }));

app.MapGet("/health", () => Results.Ok(new { status = "ok" }))
    .WithName("GetHealthStatus")
    .WithTags("Diagnostics")
    .WithSummary("Endpoint de health-check utilizado por serviço de descoberta e gateway.")
    .Produces(StatusCodes.Status200OK);

requests.MapGet("/items", getCatalogItemsHandler)
    .WithName("GetCatalogItems")
    .WithTags("Catalog")
    .WithSummary("Lista os itens fictícios disponíveis para composição das solicitações de compra.")
    .Produces<List<PurchaseItem>>(StatusCodes.Status200OK);

requests.MapGet("/items/{id:int}", getCatalogItemByIdHandler)
    .WithName("GetCatalogItemById")
    .WithTags("Catalog")
    .WithSummary("Busca um item específico do catálogo de compras pelo identificador.")
    .Produces<PurchaseItem>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status404NotFound);

requests.MapPost("/", createPurchaseRequestHandler)
    .WithName("CreatePurchaseRequest")
    .WithTags("Requests")
    .WithSummary("Cria uma nova solicitação de compra baseada nos itens do catálogo.")
    .Produces<PurchaseRequestResponse>(StatusCodes.Status201Created)
    .Produces(StatusCodes.Status400BadRequest)
    .Produces(StatusCodes.Status404NotFound);

requests.MapGet("/", getPurchaseRequestsHandler)
    .WithName("GetPurchaseRequests")
    .WithTags("Requests")
    .WithSummary("Lista as solicitações de compra cadastradas ordenadas da mais recente para a mais antiga.")
    .Produces<IEnumerable<PurchaseRequestResponse>>(StatusCodes.Status200OK);

requests.MapGet("/{id:guid}", getPurchaseRequestByIdHandler)
    .WithName("GetPurchaseRequestById")
    .WithTags("Requests")
    .WithSummary("Busca detalhes completos de uma solicitação de compra específica.")
    .Produces<PurchaseRequestResponse>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status404NotFound);

requests.MapGet("/{requestId:guid}/items/{itemId:int}", getPurchaseRequestItemHandler)
    .WithName("GetPurchaseRequestItem")
    .WithTags("Requests")
    .WithSummary("Recupera um item específico dentro de uma solicitação de compra.")
    .Produces<PurchaseRequestLineResponse>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status404NotFound);

requests.MapPost("/{id:guid}/confirm", confirmPurchaseRequestHandler)
    .WithName("ConfirmPurchaseRequest")
    .WithTags("Workflow")
    .WithSummary("Confirma manualmente uma solicitação de compra.")
    .Produces<PurchaseRequestResponse>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status400BadRequest)
    .Produces(StatusCodes.Status404NotFound);

requests.MapPost("/{id:guid}/external-approval", submitForExternalApprovalHandler)
    .WithName("SubmitPurchaseRequestForExternalApproval")
    .WithTags("Workflow")
    .WithSummary("Envia a solicitação de compra para aprovação automática no microserviço Python Capitalia.")
    .Produces(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status404NotFound)
    .Produces(StatusCodes.Status502BadGateway)
    .Produces(StatusCodes.Status503ServiceUnavailable);

requests.MapPost("/{id:guid}/reject", rejectPurchaseRequestHandler)
    .WithName("RejectPurchaseRequest")
    .WithTags("Workflow")
    .WithSummary("Rejeita manualmente uma solicitação de compra.")
    .Produces<PurchaseRequestResponse>(StatusCodes.Status200OK)
    .Produces(StatusCodes.Status400BadRequest)
    .Produces(StatusCodes.Status404NotFound);

app.MapGet("/api/items", getCatalogItemsHandler);
app.MapGet("/api/items/{id:int}", getCatalogItemByIdHandler);
app.MapPost("/api/requests", createPurchaseRequestHandler);
app.MapGet("/api/requests", getPurchaseRequestsHandler);
app.MapGet("/api/requests/{id:guid}", getPurchaseRequestByIdHandler);
app.MapGet("/api/requests/{requestId:guid}/items/{itemId:int}", getPurchaseRequestItemHandler);
app.MapPost("/api/requests/{id:guid}/confirm", confirmPurchaseRequestHandler);
app.MapPost("/api/requests/{id:guid}/external-approval", submitForExternalApprovalHandler);
app.MapPost("/api/requests/{id:guid}/reject", rejectPurchaseRequestHandler);

app.Run();
