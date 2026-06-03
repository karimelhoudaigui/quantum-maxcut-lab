import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

import { FamilyExplorer } from "./components/FamilyExplorer";
import { GraphCanvas } from "./components/GraphCanvas";
import { GraphConfigurator } from "./components/GraphConfigurator";
import { PipelineRunner } from "./components/PipelineRunner";
import { ResultsDashboard } from "./components/ResultsDashboard";

export default function App() {
  const [darkMode, setDarkMode] = useState(true);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="grid min-h-screen grid-cols-[320px_minmax(0,1fr)_380px]">
        <GraphConfigurator />
        <main className="flex min-w-0 flex-col gap-5 p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-medium uppercase text-foreground/50">Production console</p>
              <h1 className="text-3xl font-semibold">Neutral-atom MaxCut lab</h1>
            </div>
            <button
              type="button"
              onClick={() => setDarkMode((value) => !value)}
              className="rounded-md border border-border p-2 text-foreground/75 transition hover:bg-muted"
              title="Toggle theme"
            >
              {darkMode ? <Sun size={18} /> : <Moon size={18} />}
            </button>
          </div>
          <PipelineRunner />
          <GraphCanvas />
          <FamilyExplorer />
        </main>
        <ResultsDashboard />
      </div>
    </div>
  );
}
