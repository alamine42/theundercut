import { Hero, HeroTitle, HeroSubtitle } from "@/components/ui/hero";
import { CircuitRankingClient } from "./circuit-ranking-client";

export const revalidate = 300;

export const metadata = {
  title: "Circuit Rankings | The Undercut",
  description: "Rank F1 circuits by characteristics - highest speed, most tire degradation, best for overtaking, and more.",
};

export default function CircuitRankingPage() {
  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>Circuit Rankings</HeroTitle>
          <HeroSubtitle>
            Rank circuits by different characteristics
          </HeroSubtitle>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <CircuitRankingClient />
        </div>
      </section>
    </>
  );
}
