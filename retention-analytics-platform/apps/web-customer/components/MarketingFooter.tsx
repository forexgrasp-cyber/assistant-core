import Link from "next/link";

const PRODUCT_LINKS = [
  { href: "/features", label: "All features" },
  { href: "/pricing", label: "Pricing" },
  { href: "/login", label: "Sign in" },
];

const RESOURCE_LINKS = [
  { href: "/features#how-it-works", label: "How it works" },
  { href: "/features#integrations", label: "Integrations" },
  { href: "/features#analytics", label: "Analytics" },
  { href: "/features#automation", label: "Automation" },
];

export default function MarketingFooter() {
  return (
    <footer className="border-t border-[var(--border)] bg-[var(--surface)]">
      <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2 font-bold text-[var(--text)]">
            <span className="rounded bg-indigo-600 px-2 py-0.5 text-xs text-white">RA</span>
            <span className="text-sm">Snapford Retention</span>
          </div>
          <p className="mt-3 max-w-xs text-sm text-[var(--text-2)]">
            One loop that connects customer data, retention automation and measured outcomes — before
            and after, not guessed.
          </p>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-[var(--text)]">Product</h3>
          <ul className="mt-3 space-y-2">
            {PRODUCT_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-sm text-[var(--text-2)] hover:text-[var(--text)]">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-[var(--text)]">Resources</h3>
          <ul className="mt-3 space-y-2">
            {RESOURCE_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="text-sm text-[var(--text-2)] hover:text-[var(--text)]">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-sm font-semibold text-[var(--text)]">More from Snapford</h3>
          <p className="mt-3 text-sm text-[var(--text-2)]">
            Retention is one product in the Snapford portfolio.
          </p>
          <a
            href="https://snapford.com"
            target="_blank"
            rel="noreferrer noopener"
            className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-indigo-600 hover:text-indigo-500"
          >
            Browse all Snapford products
            <span aria-hidden="true">→</span>
          </a>
        </div>
      </div>

      <div className="border-t border-[var(--border)] px-5 py-5">
        <div className="mx-auto flex max-w-7xl flex-col gap-2 text-xs text-[var(--text-2)] sm:flex-row sm:items-center sm:justify-between">
          <span>© {new Date().getFullYear()} Snapford. Retention Analytics Platform.</span>
          <div className="flex gap-4">
            <a
              href="https://snapford.com"
              target="_blank"
              rel="noreferrer noopener"
              className="hover:text-[var(--text)]"
            >
              Snapford home
            </a>
            <Link href="/login" className="hover:text-[var(--text)]">
              Customer portal
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
