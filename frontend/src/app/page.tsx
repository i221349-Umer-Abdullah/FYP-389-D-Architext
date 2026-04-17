import { HeroSection } from "@/components/hero/HeroSection";
import { SiteFooter } from "@/components/layout/SiteFooter";
import { SectionShell } from "@/components/layout/SectionShell";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { AIPipelineScroll } from "@/components/pipeline/AIPipelineScroll";
import { AnimatedSectionHeading } from "@/components/scroll/AnimatedSectionHeading";
import { FeatureCards } from "@/components/scroll/FeatureCards";
import { LineRevealText } from "@/components/scroll/LineRevealText";
import { MarqueeStrip } from "@/components/scroll/MarqueeStrip";
import { ScrollDrivenShowcase } from "@/components/scroll/ScrollDrivenShowcase";
import { STORY_LINES } from "@/lib/constants";

import styles from "./page.module.css";

export default function HomePage() {
  return (
    <div className={styles.page}>
      <SiteHeader />
      <main>
        <HeroSection />
        <AIPipelineScroll />
        <MarqueeStrip text="Architext 3D Intelligence" />
        <SectionShell id="scroll-story" className={styles.storySection}>
          <AnimatedSectionHeading
            kicker="AI Spatial Reasoning"
            title="The AI reads intent, constraints, and room logic."
          />
          <LineRevealText lines={STORY_LINES} />
        </SectionShell>
        <SectionShell className={styles.featuresSection}>
          <AnimatedSectionHeading
            kicker="Generation Intelligence"
            title="From prompt to structured architectural output."
            subtitle="Architext turns natural language into room data, spatial relationships, and BIM-ready planning decisions."
          />
          <FeatureCards />
        </SectionShell>
        <ScrollDrivenShowcase />
      </main>
      <SiteFooter />
    </div>
  );
}
