using Consul;
using Microsoft.Extensions.Options;

namespace PurchaseRequestsService.Infrastructure;

public class ConsulRegistrationHostedService : IHostedService, IDisposable
{
    private readonly ConsulOptions _options;
    private readonly ILogger<ConsulRegistrationHostedService> _logger;
    private IConsulClient? _client;

    public ConsulRegistrationHostedService(IOptions<ConsulOptions> options, ILogger<ConsulRegistrationHostedService> logger)
    {
        _options = options.Value;
        _logger = logger;
    }

    public async Task StartAsync(CancellationToken cancellationToken)
    {
        if (!_options.Enabled)
        {
            _logger.LogInformation("Consul registration is disabled.");
            return;
        }

        if (!Uri.TryCreate(_options.Address, UriKind.Absolute, out var consulUri))
        {
            _logger.LogWarning("Invalid Consul address configured: {Address}", _options.Address);
            return;
        }

        if (!Uri.TryCreate(_options.ServiceAddress, UriKind.Absolute, out var serviceUri))
        {
            _logger.LogWarning("Invalid service address configured for Consul registration: {Address}", _options.ServiceAddress);
            return;
        }

        _client = new ConsulClient(config =>
        {
            config.Address = consulUri;
        });

        var registration = new AgentServiceRegistration
        {
            ID = _options.ServiceId,
            Name = _options.ServiceName,
            Address = serviceUri.Host,
            Port = serviceUri.Port,
            Check = new AgentServiceCheck
            {
                HTTP = new Uri(serviceUri, _options.HealthEndpoint).ToString(),
                Interval = TimeSpan.FromSeconds(20),
                Timeout = TimeSpan.FromSeconds(5),
                DeregisterCriticalServiceAfter = TimeSpan.FromMinutes(1)
            }
        };

        _logger.LogInformation("Registering service {Service} in Consul at {Consul}", registration.Name, consulUri);
        await _client.Agent.ServiceDeregister(registration.ID, cancellationToken);
        await _client.Agent.ServiceRegister(registration, cancellationToken);
    }

    public async Task StopAsync(CancellationToken cancellationToken)
    {
        if (_client is null || !_options.Enabled)
        {
            return;
        }

        _logger.LogInformation("Deregistering service {Service} from Consul", _options.ServiceId);
        try
        {
            await _client.Agent.ServiceDeregister(_options.ServiceId, cancellationToken);
        }
        catch (Exception ex)
        {
            _logger.LogWarning(ex, "Failed to deregister service {Service} from Consul", _options.ServiceId);
        }
    }

    public void Dispose()
    {
        _client?.Dispose();
    }
}
