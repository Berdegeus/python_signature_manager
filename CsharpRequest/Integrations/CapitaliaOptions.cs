namespace PurchaseRequestsService.Integrations;

public class CapitaliaOptions
{
    public bool Enabled { get; set; }
    public string BaseAddress { get; set; } = string.Empty;
    public string ApiKey { get; set; } = string.Empty;
}
