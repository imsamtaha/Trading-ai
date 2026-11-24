import Image from "next/image";

export function AtlasWordmark() {
  return (
    <div className="atlas-wordmark">
      <Image src="/just-ai-intelligence.webp" alt="JUST AI Intelligence" width={1280} height={1280} unoptimized priority />
    </div>
  );
}
