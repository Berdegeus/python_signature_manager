using PurchaseRequestsService.Models;

namespace PurchaseRequestsService.Transport;

public record PurchaseRequestLineResponse(
    int LineId,
    int ItemId,
    string ItemName,
    string ItemDescription,
    string Category,
    int Quantity,
    decimal UnitPrice,
    decimal LineTotal
);

public record PurchaseRequestResponse(
    Guid RequestId,
    string RequesterName,
    string Department,
    DateTime RequestedAt,
    RequestStatus Status,
    decimal TotalValue,
    string? ExternalDecision,
    string? ExternalDecisionNotes,
    DateTime? ExternalDecisionAt,
    IReadOnlyList<PurchaseRequestLineResponse> Items
);

public static class PurchaseRequestMappings
{
    public static PurchaseRequestLineResponse ToResponse(this PurchaseRequestLine line)
    {
        return new PurchaseRequestLineResponse(
            line.Id,
            line.PurchaseItemId,
            line.PurchaseItem?.Name ?? string.Empty,
            line.PurchaseItem?.Description ?? string.Empty,
            line.PurchaseItem?.Category ?? string.Empty,
            line.Quantity,
            line.UnitPrice,
            line.LineTotal
        );
    }

    public static PurchaseRequestResponse ToResponse(this PurchaseRequest entity)
    {
        var items = entity.Lines
            .OrderBy(line => line.Id)
            .Select(line => line.ToResponse())
            .ToList();

        return new PurchaseRequestResponse(
            entity.Id,
            entity.RequesterName,
            entity.Department,
            entity.RequestedAt,
            entity.Status,
            entity.TotalValue,
            entity.ExternalDecision,
            entity.ExternalDecisionNotes,
            entity.ExternalDecisionAt,
            items
        );
    }
}
