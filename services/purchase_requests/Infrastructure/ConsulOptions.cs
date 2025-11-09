namespace PurchaseRequestsService.Infrastructure;

public class ConsulOptions
{
    public bool Enabled { get; set; }
    public string Address { get; set; } = "http://localhost:8500";
    public string ServiceId { get; set; } = "purchase-requests-service";
    public string ServiceName { get; set; } = "purchase-requests-service";
    public string ServiceAddress { get; set; } = "http://localhost:5085";
    public string HealthEndpoint { get; set; } = "/health";
}
