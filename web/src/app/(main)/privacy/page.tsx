import { Hero, HeroTitle, HeroSubtitle } from "@/components/ui/hero";
import { Card, CardContent } from "@/components/ui/card";

export const metadata = {
  title: "Privacy Policy | The Undercut",
  description: "Privacy policy for The Undercut F1 analytics dashboard",
};

export default function PrivacyPage() {
  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>Privacy Policy</HeroTitle>
          <HeroSubtitle>Last updated: January 2024</HeroSubtitle>
        </div>
      </Hero>

      <section className="py-12">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="prose prose-sm max-w-none space-y-6">
              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Overview</h2>
                <p className="text-muted leading-relaxed">
                  The Undercut is an F1 analytics dashboard that provides race strategy analysis,
                  lap time data, and championship standings. We are committed to protecting your
                  privacy and being transparent about our data practices.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Data Collection</h2>
                <p className="text-muted leading-relaxed">
                  We collect minimal data necessary to operate this service:
                </p>
                <ul className="list-disc list-inside text-muted mt-2 space-y-1">
                  <li>Standard server access logs (IP addresses, timestamps, pages visited)</li>
                  <li>Analytics data via Google Analytics to understand usage patterns</li>
                  <li>No personal information is collected or stored</li>
                </ul>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Cookies</h2>
                <p className="text-muted leading-relaxed">
                  We use essential cookies for site functionality and analytics cookies to
                  understand how visitors use our site. You can disable cookies in your browser
                  settings, though this may affect site functionality.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Third-Party Services</h2>
                <p className="text-muted leading-relaxed">
                  We use the following third-party services:
                </p>
                <ul className="list-disc list-inside text-muted mt-2 space-y-1">
                  <li>Google Analytics for usage statistics</li>
                  <li>Render for hosting services</li>
                </ul>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Data Sources</h2>
                <p className="text-muted leading-relaxed">
                  All F1 race data is sourced from publicly available APIs including FastF1 and
                  OpenF1. We do not collect or store any data from users related to F1 races.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Contact</h2>
                <p className="text-muted leading-relaxed">
                  For questions about this privacy policy, please open an issue on our GitHub
                  repository.
                </p>
              </section>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
