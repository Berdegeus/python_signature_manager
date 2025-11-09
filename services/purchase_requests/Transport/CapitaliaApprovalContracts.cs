using PurchaseRequestsService.Models;

namespace PurchaseRequestsService.Transport;

public record CapitaliaApprovalRequest(
    Guid RequestId,
    string Requester,
    string Department,
    decimal TotalValue,
    IReadOnlyCollection<CapitaliaApprovalItem> Items
)
{
    public static CapitaliaApprovalRequest FromEntity(PurchaseRequest request)
    {
        var items = request.Lines
            .OrderBy(line => line.Id)
            .Select(line => new CapitaliaApprovalItem(
                line.PurchaseItemId,
                line.PurchaseItem?.Name ?? string.Empty,
                line.Quantity,
                line.UnitPrice,
                line.LineTotal
            ))
            .ToList();

        return new CapitaliaApprovalRequest(
            request.Id,
            request.RequesterName,
            request.Department,
            request.TotalValue,
            items
        );
    }
}

public record CapitaliaApprovalItem(
    int ItemId,
    string Name,
    int Quantity,
    decimal UnitPrice,
    decimal LineTotal
);

public record CapitaliaApprovalResponse(
    bool Approved,
    string Decision,
    string? Notes
);
