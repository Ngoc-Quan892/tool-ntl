import { DerivedRoad } from "./DerivedRoad";
import { RoadmapMatrix } from "../types";

interface Props {
  data?: RoadmapMatrix;
}

export const SmallRoad = ({ data }: Props) => (
  <DerivedRoad 
    title="Small Road" 
    icon="🔴"
    description="Derived from Big Eye Boy"
    data={data} 
  />
);

export default SmallRoad;
