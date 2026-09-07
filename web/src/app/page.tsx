import Hero from "@/components/Hero";
import HowItWorks from "@/components/HowItWorks";
import TechStack from "@/components/TechStack";
import ApiSection from "@/components/ApiSection";
import Footer from "@/components/Footer";

export default function Home() {
  return (
    <main>
      <Hero />
      <HowItWorks />
      <TechStack />
      <ApiSection />
      <Footer />
    </main>
  );
}
