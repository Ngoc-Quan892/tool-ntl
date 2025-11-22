import { DerivedRoad } from "./DerivedRoad";
import { RoadmapMatrix } from "../types";

interface Props {
  data?: RoadmapMatrix;
}

export const BigEyeBoy = ({ data }: Props) => (
  <DerivedRoad 
    title="Big Eye Boy" 
    icon="🔵"
    description="Derived from Big Road"
    data={data} 
  />
);

export default BigEyeBoy;
