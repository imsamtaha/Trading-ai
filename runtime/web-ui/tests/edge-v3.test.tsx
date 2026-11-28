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
it.each(["LOCAL_RESEARCH_REPORT","STALE"])("renders %s cost evidence",async(report_state)=>{
 const cost_stress=Object.fromEntries(["1.0","1.5","2.0"].map((scale,i)=>[scale,{observations:200,mean_net_r:.2-i*.05,expectancy_lower_r:.1-i*.04,status:"SHADOW_REVIEW"}]));
 vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({stage:"RESEARCH_ONLY",decision:"ABSTAIN",report_state,broker_execution_allowed:false,live_activation_allowed:false,worker_verified:false,sample_count:200,input_kind:"HISTORICAL_USER_SUPPLIED",cost_stress}),{status:200})));
 render(<EdgeV3Panel/>);
 expect(await screen.findByText(report_state)).toBeInTheDocument();
 expect(screen.getByRole("table")).toBeInTheDocument();
 for(const scale of ["1.0","1.5","2.0"])expect(screen.getByText(`${scale}×`)).toBeInTheDocument();
 expect(screen.getByText("0.2000")).toBeInTheDocument();
 expect(screen.getByText("0.0200")).toBeInTheDocument();
});
