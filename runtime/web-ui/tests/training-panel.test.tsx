import {render,screen,waitFor} from "@testing-library/react";
import {afterEach,expect,it,vi} from "vitest";
import {TrainingPanel} from "@/features/training/training-panel";
afterEach(()=>vi.unstubAllGlobals());
it("reports unavailable instead of inventing zero trades",async()=>{
 vi.stubGlobal("fetch",vi.fn(async()=>new Response("{}",{status:503})));
 render(<TrainingPanel language="en"/>);
 expect(await screen.findByRole("alert")).toHaveTextContent("Training data unavailable");
 expect(screen.queryByText("0 / 100")).not.toBeInTheDocument();
});
it("keeps the selector waiting for a third day despite enough results",async()=>{
 vi.stubGlobal("fetch",vi.fn(async()=>new Response(JSON.stringify({checked_at:"2026-10-08T23:00:00Z",mode:"PAPER",unavailable:[],portfolio:{closed:106,open:5,entries_today_utc:80,daily_ceiling:100,sum_r:-81.1},selector:{samples:106,minimum_samples:100,days:2,minimum_days:3,status:"INSUFFICIENT_DATA",data_gates_met:false},agents:[{agent:"technical",weight:0.8065,weight_change:null,samples:106,brier_score:0.5617}],asset_classes:[],rejections:null}),{status:200})));
 render(<TrainingPanel language="en"/>);
 expect(await screen.findByText("106 / 100")).toBeInTheDocument();
 expect(screen.getByText("2 / 3")).toBeInTheDocument();
 expect(screen.getByText("Waiting for more data")).toBeInTheDocument();
 expect(screen.getByText(/Weight is influence/)).toBeInTheDocument();
 expect(screen.getByText(/Spread included/)).toBeInTheDocument();
});
it("uses owner endpoint and rejects unprivileged responses",async()=>{
 const f=vi.fn(async()=>new Response("{}",{status:403}));vi.stubGlobal("fetch",f);
 render(<TrainingPanel language="ar"/>);
 await waitFor(()=>expect(f).toHaveBeenCalled());
 expect(f).toHaveBeenCalledWith("/backend/api/runtime/training", expect.objectContaining({credentials:"same-origin",cache:"no-store"}));
 expect(await screen.findByRole("alert")).toHaveTextContent("بيانات التدريب غير متاحة");
});
