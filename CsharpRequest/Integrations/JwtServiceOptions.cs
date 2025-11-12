namespace PurchaseRequestsService.Integrations;

public class JwtServiceOptions
{
    public bool Enabled { get; set; } = true;
    public string BaseAddress { get; set; } = "http://127.0.0.1:8200";
    public string ClientId { get; set; } = "purchase-requests-service";
    public string Audience { get; set; } = "capitalia";
    public int DefaultTtlSeconds { get; set; } = 600;
    public Dictionary<string, string> ExtraClaims { get; set; } = new();
    public int TimeoutSeconds { get; set; } = 5;
}
