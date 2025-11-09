using System.Net.Http.Json;
using Microsoft.Extensions.Options;
using PurchaseRequestsService.Models;
using PurchaseRequestsService.Transport;

namespace PurchaseRequestsService.Integrations;

public class CapitaliaApprovalClient
{
    private readonly HttpClient _httpClient;
    private readonly CapitaliaOptions _options;
    private readonly ILogger<CapitaliaApprovalClient> _logger;

    public CapitaliaApprovalClient(HttpClient httpClient, IOptions<CapitaliaOptions> options, ILogger<CapitaliaApprovalClient> logger)
    {
        _httpClient = httpClient;
        _options = options.Value;
        _logger = logger;
    }

    public bool IsEnabled => _options.Enabled && !string.IsNullOrWhiteSpace(_httpClient.BaseAddress?.ToString());

    public async Task<CapitaliaApprovalResponse?> RequestApprovalAsync(PurchaseRequest request, CancellationToken cancellationToken)
    {
        if (!IsEnabled)
        {
            _logger.LogWarning("Capitalia integration is disabled.");
            return null;
        }

        var payload = CapitaliaApprovalRequest.FromEntity(request);
        using var requestMessage = new HttpRequestMessage(HttpMethod.Post, "api/v1/purchase-approvals")
        {
            Content = JsonContent.Create(payload)
        };

        if (!string.IsNullOrWhiteSpace(_options.ApiKey))
        {
            requestMessage.Headers.Add("X-API-Key", _options.ApiKey);
        }

        var response = await _httpClient.SendAsync(requestMessage, cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var body = await response.Content.ReadAsStringAsync(cancellationToken);
            _logger.LogWarning("Capitalia API responded with {Status}: {Body}", response.StatusCode, body);
            return null;
        }

        return await response.Content.ReadFromJsonAsync<CapitaliaApprovalResponse>(cancellationToken: cancellationToken);
    }
}
