using System.Net.Http.Json;
using System.Text.Json.Serialization;
using Microsoft.Extensions.Options;

namespace PurchaseRequestsService.Integrations;

public class JwtServiceClient
{
    private readonly HttpClient _httpClient;
    private readonly JwtServiceOptions _options;
    private readonly ILogger<JwtServiceClient> _logger;

    public JwtServiceClient(HttpClient httpClient, IOptions<JwtServiceOptions> options, ILogger<JwtServiceClient> logger)
    {
        _httpClient = httpClient;
        _options = options.Value;
        _logger = logger;
    }

    public bool IsEnabled => _options.Enabled && _httpClient.BaseAddress is not null;

    public async Task<string?> TryIssueTokenAsync(CancellationToken cancellationToken)
    {
        if (!IsEnabled)
        {
            return null;
        }

        var payload = new JwtTokenRequest
        {
            Claims = BuildClaims(),
            Ttl = _options.DefaultTtlSeconds
        };

        try
        {
            using var response = await _httpClient.PostAsJsonAsync("/token", payload, cancellationToken);
            if (!response.IsSuccessStatusCode)
            {
                var errorBody = await response.Content.ReadAsStringAsync(cancellationToken);
                _logger.LogWarning(
                    "JWT service responded with {StatusCode}. Body: {Body}",
                    response.StatusCode,
                    errorBody);
                return null;
            }

            var token = await response.Content.ReadFromJsonAsync<JwtTokenResponse>(cancellationToken: cancellationToken);
            return token?.Token;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Failed to issue token from jwt-service");
            return null;
        }
    }

    private Dictionary<string, object> BuildClaims()
    {
        var claims = new Dictionary<string, object>
        {
            ["sub"] = _options.ClientId,
            ["iss"] = _options.ClientId,
            ["service"] = "purchase_requests"
        };

        if (!string.IsNullOrWhiteSpace(_options.Audience))
        {
            claims["aud"] = _options.Audience;
        }

        foreach (var extra in _options.ExtraClaims)
        {
            claims[extra.Key] = extra.Value;
        }

        return claims;
    }

    private sealed class JwtTokenRequest
    {
        [JsonPropertyName("claims")]
        public Dictionary<string, object> Claims { get; set; } = new();

        [JsonPropertyName("ttl")]
        public int Ttl { get; set; }
    }

    private sealed class JwtTokenResponse
    {
        [JsonPropertyName("token")]
        public string? Token { get; set; }
    }
}
