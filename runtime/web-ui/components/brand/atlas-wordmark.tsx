import Image from "next/image";

export function AtlasWordmark() {
  return (
    <div className="atlas-wordmark">
      <Image src="/atlas-logo.webp" alt="ATLAS" width={1254} height={1254} unoptimized priority />
    </div>
  );
}
