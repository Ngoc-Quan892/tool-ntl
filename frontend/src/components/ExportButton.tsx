import { useState } from "react";
import { Download, FileText, FileSpreadsheet, Loader } from "lucide-react";
import { useToastStore } from "../stores/toastStore";

interface ExportButtonProps {
  format?: "csv" | "json";
  className?: string;
}

export const ExportButton = ({ format = "csv", className = "" }: ExportButtonProps) => {
  const [isExporting, setIsExporting] = useState(false);
  const { success, error } = useToastStore();

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // Try v2 API first
      const response = await fetch(`/api/v2/hands/history?limit=1000&format=${format}`);
      
      if (!response.ok) {
        // Fallback to v1
        const v1Response = await fetch(`/api/export?format=${format}`);
        if (!v1Response.ok) {
          throw new Error("Export failed");
        }
        
        const blob = await v1Response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `baccarat-data.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `baccarat-data.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      }
      
      success(`Data exported as ${format.toUpperCase()}`);
    } catch (err: any) {
      error(`Export failed: ${err?.message || "Unknown error"}`);
    } finally {
      setIsExporting(false);
    }
  };

  const Icon = format === "csv" ? FileSpreadsheet : FileText;

  return (
    <button
      onClick={handleExport}
      disabled={isExporting}
      className={`
        px-6 py-3 rounded-xl border border-slate-600 text-slate-200 
        hover:bg-slate-800 transition-colors flex items-center gap-2
        disabled:opacity-50 disabled:cursor-not-allowed
        ${className}
      `}
      title={`Export as ${format.toUpperCase()}`}
    >
      {isExporting ? (
        <>
          <Loader size={18} className="animate-spin" />
          Exporting...
        </>
      ) : (
        <>
          <Icon size={18} />
          <Download size={18} />
          Export {format.toUpperCase()}
        </>
      )}
    </button>
  );
};

export default ExportButton;

