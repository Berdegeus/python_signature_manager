using System.ComponentModel.DataAnnotations.Schema;

namespace PurchaseRequestsService.Models;

public class PurchaseRequestLine
{
    public int Id { get; set; }

    public Guid PurchaseRequestId { get; set; }
    public PurchaseRequest? PurchaseRequest { get; set; }

    public int PurchaseItemId { get; set; }
    public PurchaseItem? PurchaseItem { get; set; }

    public int Quantity { get; set; }

    [Column(TypeName = "decimal(18,2)")]
    public decimal UnitPrice { get; set; }

    [Column(TypeName = "decimal(18,2)")]
    public decimal LineTotal { get; set; }
}
