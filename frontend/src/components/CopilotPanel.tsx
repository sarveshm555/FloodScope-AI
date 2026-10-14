import React, { useState } from 'react';
import { Bot, FileText, Sparkles, Copy, Check, AlertTriangle } from 'lucide-react';
import { BackendHealth, SituationReportResponse } from '../types';

interface CopilotPanelProps {
  health: BackendHealth | null;
  reportData?: SituationReportResponse | null;
  loading?: boolean;
}

export const CopilotPanel: React.FC<CopilotPanelProps> = ({
  health,
  reportData,
  loading = false,
}) => {
  const [language, setLanguage] = useState<'en' | 'ne'>('en');
  const [copied, setCopied] = useState(false);

  const llmActive = health?.services.llm_provider_configured ?? false;

  const handleCopy = () => {
    if (!reportData) return;
    const text = language === 'en' ? reportData.english_report : reportData.nepali_report;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
        <div className="flex items-center space-x-2">
          <Bot className="w-5 h-5 text-sky-400" />
          <h2 className="font-semibold text-slate-200">Situation-Report Copilot</h2>
        </div>

        {/* Language Toggle */}
        <div className="flex items-center space-x-1 bg-slate-800 p-0.5 rounded-lg border border-slate-700 text-xs">
          <button
            onClick={() => setLanguage('en')}
            className={`px-2.5 py-1 rounded font-medium transition ${
              language === 'en'
                ? 'bg-sky-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('ne')}
            className={`px-2.5 py-1 rounded font-medium transition ${
              language === 'ne'
                ? 'bg-sky-600 text-white'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            नेपाली
          </button>
        </div>
      </div>

      {/* Mode Status Pill */}
      <div className="flex items-center justify-between text-xs px-3 py-2 rounded-lg bg-slate-950/70 border border-slate-800">
        <span className="text-slate-400">Operating Mode:</span>
        {llmActive ? (
          <span className="flex items-center text-indigo-400 font-medium">
            <Sparkles className="w-3.5 h-3.5 mr-1" />
            LLM Copilot ({health?.services.llm_provider_name}) + Schema Grounding
          </span>
        ) : (
          <span className="flex items-center text-emerald-400 font-medium">
            Verified Deterministic Evidence Engine (Offline Safe)
          </span>
        )}
      </div>

      {loading ? (
        <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-6 text-center space-y-2">
          <Bot className="w-6 h-6 text-sky-400 mx-auto animate-bounce" />
          <p className="text-xs text-slate-300">Generating grounded bilingual situation report...</p>
        </div>
      ) : !reportData ? (
        <div className="space-y-4">
          <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-5 text-center">
            <FileText className="w-6 h-6 text-slate-500 mx-auto mb-2" />
            <h3 className="text-xs font-semibold text-slate-300">
              {language === 'en' ? 'Awaiting Validated Spatial Data' : 'कुनै प्रमाणीकृत नतिजा उपलब्ध छैन'}
            </h3>
            <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
              {language === 'en'
                ? 'Execute the analysis pipeline to generate verifiable situation reports in English and Nepali.'
                : 'स्थिति प्रतिवेदन तयार गर्न भौगोलिक विश्लेषण सुरु गर्नुहोस्।'}
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Provenance: {reportData.data_sources.length} Verified Sources</span>
            <button
              onClick={handleCopy}
              className="flex items-center space-x-1 px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Copied' : 'Copy Report'}</span>
            </button>
          </div>

          <div className="p-4 bg-slate-950 rounded-lg border border-slate-800 font-sans text-xs text-slate-300 leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap">
            {language === 'en' ? reportData.english_report : reportData.nepali_report}
          </div>

          {reportData.is_hypothetical_scenario && (
            <div className="p-2.5 rounded bg-amber-950/40 border border-amber-800/60 text-[11px] text-amber-300/90 flex items-start gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
              <span>
                <strong>Grounding Notice:</strong> This report is grounded in real Copernicus DEM topography and real OpenStreetMap infrastructure using a parameterized river stage scenario.
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
