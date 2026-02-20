import { Hero, HeroTitle, HeroSubtitle } from "@/components/ui/hero";
import { Card, CardContent } from "@/components/ui/card";

export const metadata = {
  title: "Terms of Service | The Undercut",
  description: "Terms of service for The Undercut F1 analytics dashboard",
};

export default function TermsPage() {
  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>Terms of Service</HeroTitle>
          <HeroSubtitle>Last updated: January 2024</HeroSubtitle>
        </div>
      </Hero>

      <section className="py-12">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="prose prose-sm max-w-none space-y-6">
              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Acceptance of Terms</h2>
                <p className="text-muted leading-relaxed">
                  By accessing and using The Undercut, you accept and agree to be bound by these
                  Terms of Service. If you do not agree to these terms, please do not use this
                  service.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Service Description</h2>
                <p className="text-muted leading-relaxed">
                  The Undercut is a free F1 analytics dashboard that provides race strategy
                  analysis, lap time visualization, and championship standings. The service is
                  provided "as is" without warranty of any kind.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Use of Data</h2>
                <p className="text-muted leading-relaxed">
                  All F1 race data displayed on this site is sourced from public APIs and is
                  provided for informational purposes only. We make no guarantees about the
                  accuracy, completeness, or timeliness of the data.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Intellectual Property</h2>
                <p className="text-muted leading-relaxed">
                  The Undercut is not affiliated with, endorsed by, or sponsored by Formula 1,
                  FIA, or any F1 team. Formula 1, F1, and related marks are trademarks of Formula
                  One Licensing BV.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Limitation of Liability</h2>
                <p className="text-muted leading-relaxed">
                  In no event shall The Undercut or its operators be liable for any indirect,
                  incidental, special, consequential, or punitive damages arising out of your
                  use of the service.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Modifications</h2>
                <p className="text-muted leading-relaxed">
                  We reserve the right to modify or discontinue the service at any time without
                  notice. We also reserve the right to update these terms at any time.
                </p>
              </section>

              <section>
                <h2 className="font-serif text-xl font-semibold mb-3">Contact</h2>
                <p className="text-muted leading-relaxed">
                  For questions about these terms, please open an issue on our GitHub repository.
                </p>
              </section>
            </CardContent>
          </Card>
        </div>
      </section>
    </>
  );
}
