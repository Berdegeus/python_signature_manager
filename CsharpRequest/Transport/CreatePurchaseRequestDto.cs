using System.ComponentModel.DataAnnotations;

namespace PurchaseRequestsService.Transport;

public class CreatePurchaseRequestDto
{
    [Required]
    [MaxLength(120)]
    public string RequesterName { get; set; } = string.Empty;

    [MaxLength(240)]
    public string Department { get; set; } = string.Empty;

    [MinLength(1)]
    public List<CreatePurchaseRequestLineDto> Items { get; set; } = new();
}

public class CreatePurchaseRequestLineDto
{
    [Range(1, int.MaxValue)]
    public int ItemId { get; set; }

    [Range(1, 1000)]
    public int Quantity { get; set; }
}
