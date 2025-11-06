using Microsoft.EntityFrameworkCore;
using PurchaseRequestsService.Models;

namespace PurchaseRequestsService.Data;

public class PurchaseRequestContext : DbContext
{
    public PurchaseRequestContext(DbContextOptions<PurchaseRequestContext> options) : base(options)
    {
    }

    public DbSet<PurchaseItem> PurchaseItems => Set<PurchaseItem>();
    public DbSet<PurchaseRequest> PurchaseRequests => Set<PurchaseRequest>();
    public DbSet<PurchaseRequestLine> PurchaseRequestLines => Set<PurchaseRequestLine>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<PurchaseRequest>(entity =>
        {
            entity.HasMany(e => e.Lines)
                .WithOne(e => e.PurchaseRequest)
                .HasForeignKey(e => e.PurchaseRequestId);

            entity.Property(e => e.Status)
                .HasConversion<string>()
                .HasMaxLength(20);

            entity.Property(e => e.TotalValue)
                .HasPrecision(18, 2);

            entity.Property(e => e.ExternalDecision)
                .HasMaxLength(80);

            entity.Property(e => e.ExternalDecisionNotes)
                .HasMaxLength(240);
        });

        modelBuilder.Entity<PurchaseRequestLine>(entity =>
        {
            entity.Property(e => e.UnitPrice)
                .HasPrecision(18, 2);

            entity.Property(e => e.LineTotal)
                .HasPrecision(18, 2);
        });

        modelBuilder.Entity<PurchaseItem>(entity =>
        {
            entity.Property(e => e.UnitPrice)
                .HasPrecision(18, 2);

            entity.HasData(
                new PurchaseItem
                {
                    Id = 1,
                    Name = "Cloud Object Storage - Capacity Pack",
                    Description = "Annual subscription for 5 TB of cloud object storage with redundancy",
                    Category = "Storage",
                    UnitPrice = 1299.00m,
                    Active = true
                },
                new PurchaseItem
                {
                    Id = 2,
                    Name = "Analytics Workstation Instance",
                    Description = "Managed virtual machine with 8 vCPU and 32 GB RAM for data analysis",
                    Category = "Compute",
                    UnitPrice = 1899.00m,
                    Active = true
                },
                new PurchaseItem
                {
                    Id = 3,
                    Name = "API Gateway Throughput Bundle",
                    Description = "Monthly allocation for 5 million API calls including monitoring",
                    Category = "Integration",
                    UnitPrice = 450.00m,
                    Active = true
                },
                new PurchaseItem
                {
                    Id = 4,
                    Name = "Developer Productivity Toolkit",
                    Description = "Bundle with CI/CD runner minutes, code quality scanning and support",
                    Category = "Tooling",
                    UnitPrice = 275.00m,
                    Active = true
                }
            );
        });
    }
}
