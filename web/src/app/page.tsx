import Hero from "@/components/Hero";
import SpecBand from "@/components/SpecBand";
import HowItWorks from "@/components/HowItWorks";
import Guardrails from "@/components/Guardrails";
import TechStack from "@/components/TechStack";
import ApiSection from "@/components/ApiSection";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main>
      <Hero />
      <SpecBand />
      <HowItWorks />
      <Guardrails />
      <TechStack />
      <ApiSection />
      <Footer />
    </main>
  );
}
