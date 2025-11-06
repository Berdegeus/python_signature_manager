using System.ComponentModel.DataAnnotations;
using System.ComponentModel.DataAnnotations.Schema;

namespace PurchaseRequestsService.Models;

public class PurchaseRequest
{
    public Guid Id { get; set; } = Guid.NewGuid();

    [MaxLength(120)]
    public string RequesterName { get; set; } = string.Empty;

    [MaxLength(240)]
    public string Department { get; set; } = string.Empty;

    public DateTime RequestedAt { get; set; } = DateTime.UtcNow;

    public RequestStatus Status { get; set; } = RequestStatus.Pending;

    [Column(TypeName = "decimal(18,2)")]
    public decimal TotalValue { get; set; }

    [MaxLength(80)]
    public string? ExternalDecision { get; set; }

    [MaxLength(240)]
    public string? ExternalDecisionNotes { get; set; }

    public DateTime? ExternalDecisionAt { get; set; }

    public ICollection<PurchaseRequestLine> Lines { get; set; } = new List<PurchaseRequestLine>();
}
