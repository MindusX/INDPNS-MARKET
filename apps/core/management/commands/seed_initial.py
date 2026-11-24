from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.catalog.models import Category, Technology
from apps.licenses.models import LicenseType
from apps.sellers.models import SellerPlan

PLANS = [
    dict(code="starter", name="Starter", sort_order=1, price_monthly=0, price_yearly=0, commission_rate="0.1500",
         tagline="Open your shop and start selling.",
         features=["Your own shop page", "Publish after moderation", "Basic sales statistics", "Standard commission"]),
    dict(code="pro", name="Pro", sort_order=2, price_monthly="19.00", price_yearly="190.00", commission_rate="0.1000", is_featured=True,
         tagline="For creators who sell regularly.",
         features=["Advanced statistics", "Promotion tools", "Advanced product management", "Priority support (per conditions)", "Reduced commission"]),
    dict(code="business", name="Business", sort_order=3, price_monthly="49.00", price_yearly="490.00", commission_rate="0.0700", contact_only=True,
         tagline="For teams and studios.",
         features=["Team seats", "Commercial tools", "Advanced analytics", "Dedicated support (per contract)", "Lowest commission"]),
]
LICENSES = [
    dict(code="personal", name="Personal", sort_order=1, summary="For one person, non-commercial projects.",
         rights=["Use in one personal, non-commercial project", "Receive all future updates of the product"],
         restrictions=["No use in projects that generate revenue", "No resale or redistribution"]),
    dict(code="commercial", name="Commercial", sort_order=2, summary="For one commercial end product.",
         rights=["Use in one commercial project or client project", "Receive all future updates of the product"],
         restrictions=["End product must not be sold as a template or theme", "No resale or redistribution of the source"]),
    dict(code="extended", name="Extended", sort_order=3, summary="For products sold to many end users.",
         rights=["Use in a product distributed or sold to multiple end users", "Receive all future updates of the product"],
         restrictions=["No resale of the item itself on any marketplace"]),
]
CATEGORIES = {
    "Source code": ["Web apps", "Mobile apps", "Scripts"],
    "Templates & themes": ["Website templates", "Admin dashboards", "Email templates"],
    "Plugins & extensions": ["CMS plugins", "Browser extensions", "IDE extensions"],
    "UI components": ["React", "Vue", "CSS & design kits"],
    "AI tools & agents": ["AI agents", "Prompts & workflows", "Automations"],
    "SDKs & libraries": ["Python", "JavaScript", "APIs & SDKs"],
}
TECHS = ["Python", "Django", "Flask", "JavaScript", "TypeScript", "React", "Vue", "Node.js", "PHP", "Laravel", "Flutter", "Swift", "Kotlin", "Tailwind CSS", "PostgreSQL", "Docker"]


class Command(BaseCommand):
    help = "Seeds plans, license types, categories and technologies (idempotent, never deletes)."

    def handle(self, *args, **opts):
        for p in PLANS:
            code = p.pop("code")
            SellerPlan.objects.get_or_create(code=code, defaults={**p, "price_monthly": Decimal(str(p["price_monthly"])),
                                                                  "price_yearly": Decimal(str(p["price_yearly"])), "commission_rate": Decimal(p["commission_rate"])})
        for l in LICENSES:
            code = l.pop("code")
            LicenseType.objects.get_or_create(code=code, defaults=l)
        for i, (parent, kids) in enumerate(CATEGORIES.items()):
            pc, _ = Category.objects.get_or_create(slug=slugify(parent), defaults={"name": parent, "order": i})
            for j, k in enumerate(kids):
                Category.objects.get_or_create(slug=slugify(f"{parent}-{k}"), defaults={"name": k, "parent": pc, "order": j})
        for t in TECHS:
            Technology.objects.get_or_create(slug=slugify(t), defaults={"name": t})
        self.stdout.write(self.style.SUCCESS("Seed complete."))
