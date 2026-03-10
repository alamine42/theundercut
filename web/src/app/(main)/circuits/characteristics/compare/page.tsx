import { Hero, HeroTitle, HeroSubtitle } from "@/components/ui/hero";
import { fetchCircuitsCharacteristics } from "@/lib/api";
import { CircuitCompareClient } from "./circuit-compare-client";

export const revalidate = 300;

export const metadata = {
  title: "Compare Circuits | The Undercut",
  description: "Compare F1 circuit characteristics side by side - tire degradation, overtaking difficulty, downforce levels, and more.",
};

export default async function CircuitComparePage() {
  const data = await fetchCircuitsCharacteristics();

  return (
    <>
      <Hero>
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <HeroTitle>Compare Circuits</HeroTitle>
          <HeroSubtitle>
            Select 2-5 circuits to compare their characteristics
          </HeroSubtitle>
        </div>
      </Hero>

      <section className="py-8 sm:py-12">
        <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
          <CircuitCompareClient circuits={data.circuits} />
        </div>
      </section>
    </>
  );
}
