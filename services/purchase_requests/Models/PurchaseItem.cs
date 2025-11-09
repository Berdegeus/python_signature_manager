namespace PurchaseRequestsService.Models;

public class PurchaseItem
{
    public int Id { get; set; }
    public string Name { get; set; } = string.Empty;
    public string Description { get; set; } = string.Empty;
    public decimal UnitPrice { get; set; }
    public string Category { get; set; } = string.Empty;
    public bool Active { get; set; } = true;
}
