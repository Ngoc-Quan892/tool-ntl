import { useState } from "react";
import { RoadmapPayload } from "../types";
import BigRoad from "./BigRoad";
import BigEyeBoy from "./BigEyeBoy";
import SmallRoad from "./SmallRoad";
import CockroachPig from "./CockroachPig";
import * as Tabs from "@radix-ui/react-tabs";
import { Grid, LayoutGrid } from "lucide-react";

interface Props {
  data?: RoadmapPayload;
}

export const RoadmapGrid = ({ data }: Props) => {
  const [viewMode, setViewMode] = useState<"grid" | "tabs">("grid");

  if (!data) {
    return (
      <div className="bg-casino-card border border-casino-border rounded-2xl p-8 text-center">
        <div className="text-4xl mb-4">📊</div>
        <div className="text-slate-400">Đang tải roadmap...</div>
      </div>
    );
  }

  if (viewMode === "tabs") {
    return (
      <div className="bg-casino-card border border-casino-border rounded-2xl p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-casino-gold">Roadmaps</h2>
          <div className="flex gap-2">
            <button
              onClick={() => setViewMode("grid")}
              className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
              title="Grid view"
            >
              <Grid size={20} />
            </button>
            <button
              onClick={() => setViewMode("tabs")}
              className="p-2 rounded-lg bg-casino-gold text-black"
              title="Tab view"
            >
              <LayoutGrid size={20} />
            </button>
          </div>
        </div>
        
        <Tabs.Root defaultValue="bigroad" className="w-full">
          <Tabs.List className="flex gap-2 mb-4">
            <Tabs.Trigger
              value="bigroad"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 data-[state=active]:bg-casino-gold data-[state=active]:text-black transition-colors"
            >
              Big Road
            </Tabs.Trigger>
            <Tabs.Trigger
              value="bigeyeboy"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 data-[state=active]:bg-casino-gold data-[state=active]:text-black transition-colors"
            >
              Big Eye Boy
            </Tabs.Trigger>
            <Tabs.Trigger
              value="smallroad"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 data-[state=active]:bg-casino-gold data-[state=active]:text-black transition-colors"
            >
              Small Road
            </Tabs.Trigger>
            <Tabs.Trigger
              value="cockroachpig"
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 data-[state=active]:bg-casino-gold data-[state=active]:text-black transition-colors"
            >
              Cockroach Pig
            </Tabs.Trigger>
          </Tabs.List>
          
          <Tabs.Content value="bigroad">
            <BigRoad data={data.big_road} highlightPatterns={true} />
          </Tabs.Content>
          <Tabs.Content value="bigeyeboy">
            <BigEyeBoy data={data.big_eye_boy} />
          </Tabs.Content>
          <Tabs.Content value="smallroad">
            <SmallRoad data={data.small_road} />
          </Tabs.Content>
          <Tabs.Content value="cockroachpig">
            <CockroachPig data={data.cockroach_pig} />
          </Tabs.Content>
        </Tabs.Root>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-casino-gold">📊 Roadmaps</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className="p-2 rounded-lg bg-casino-gold text-black"
            title="Grid view"
          >
            <Grid size={20} />
          </button>
          <button
            onClick={() => setViewMode("tabs")}
            className="p-2 rounded-lg hover:bg-slate-800 transition-colors"
            title="Tab view"
          >
            <LayoutGrid size={20} />
          </button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <BigRoad data={data.big_road} highlightPatterns={true} />
        <BigEyeBoy data={data.big_eye_boy} />
        <SmallRoad data={data.small_road} />
        <CockroachPig data={data.cockroach_pig} />
      </div>
    </div>
  );
};

export default RoadmapGrid;
