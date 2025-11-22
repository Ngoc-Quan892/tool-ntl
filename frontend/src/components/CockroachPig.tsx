import { DerivedRoad } from "./DerivedRoad";
import { RoadmapMatrix } from "../types";

interface Props {
  data?: RoadmapMatrix;
}

export const CockroachPig = ({ data }: Props) => (
  <DerivedRoad 
    title="Cockroach Pig" 
    icon="🟢"
    description="Derived from Small Road"
    data={data} 
  />
);

export default CockroachPig;
