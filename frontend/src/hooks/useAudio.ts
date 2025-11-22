export const useAudio = () => {
  const playConfidence = (confidence: number) => {
    const file = confidence > 85 ? "/sounds/high-confidence.mp3" : "/sounds/medium-confidence.mp3";
    const audio = new Audio(file);
    audio.volume = 0.3;
    audio.play();
  };

  const playClick = () => {
    const audio = new Audio("/sounds/button-click.mp3");
    audio.volume = 0.3;
    audio.play();
  };

  const playReset = () => {
    const audio = new Audio("/sounds/reset.mp3");
    audio.volume = 0.3;
    audio.play();
  };

  return { playConfidence, playClick, playReset };
};
