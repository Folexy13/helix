"use client";

import { useHelixStore } from "@/store/helixStore";
import HitlDrawer from "./HitlDrawer";

export default function HitlDrawerWrapper() {
  const { pendingCheckpoints } = useHelixStore();
  const currentId = pendingCheckpoints[0]?.id;

  // Using currentId as a key forces the HitlDrawer to re-mount
  // and reset its internal state (inputs) whenever a new checkpoint arrives.
  return <HitlDrawer key={currentId || 'none'} />;
}
