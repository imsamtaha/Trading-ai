import type { ReactElement } from "react";

export function AtlasWordmark(): ReactElement {
  return (
    <a className="atlas-wordmark" href="/" aria-label="ATLAS Trading Intelligence home">
      <span className="atlas-wordmark__name">ATLAS</span>
      <span className="atlas-wordmark__descriptor">Trading Intelligence</span>
    </a>
  );
}
