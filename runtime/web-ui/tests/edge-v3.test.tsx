import {render,screen} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {EdgeV3Panel} from "@/features/training/edge-v3-panel";
afterEach(()=>vi.unstubAllGlobals());
it("shows unavailable without fabricated performance",async()=>{
 const fetcher=vi.fn(async()=>new Response(JSON.stringify({stage:"RESEARCH_ONLY",decision:"ABSTAIN",report_state:"UNAVAILABLE",broker_execution_allowed:false,live_activation_allowed:false,worker_verified:false}),{status:200}));
 vi.stubGlobal("fetch",fetcher);render(<EdgeV3Panel/>);
 expect(await screen.findByText("UNAVAILABLE")).toBeInTheDocument();
 expect(screen.queryByRole("table")).not.toBeInTheDocument();
 expect(fetcher).toHaveBeenCalledWith("/backend/api/runtime/edge-v3",expect.objectContaining({credentials:"same-origin",cache:"no-store"}));
});
it("rejects an activating or unprivileged response",async()=>{
 vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({stage:"LIVE",decision:"BUY",broker_execution_allowed:true}),{status:200})));
 render(<EdgeV3Panel/>);expect(await screen.findByRole("alert")).toHaveTextContent("مش متاح");
 expect(screen.queryByText("BUY")).not.toBeInTheDocument();
});
