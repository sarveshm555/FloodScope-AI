import React, { useState } from 'react';
import { Bot, FileText, Send, Sparkles } from 'lucide-react';
import { BackendHealth } from '../types';

interface CopilotPanelProps {
  health: BackendHealth | null;
  analysisRun: boolean;
}

export const CopilotPanel: React.FC<CopilotPanelProps> = ({ health, analysisRun }) => {
  const [language, setLanguage] = useState<'en' | 'ne'>('en');
  const [question, setQuestion] = useState('');

  const llmActive = health?.services.llm_provider_configured ?? false;

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
          <span className="flex items-center text-amber-400 font-medium">
            Deterministic Rule-Based Generator (Offline Safe)
          </span>
        )}
      </div>

      {!analysisRun ? (
        <div className="space-y-4">
          <div className="bg-slate-950/70 border border-dashed border-slate-800 rounded-lg p-5 text-center">
            <FileText className="w-6 h-6 text-slate-500 mx-auto mb-2" />
            <h3 className="text-xs font-semibold text-slate-300">
              {language === 'en' ? 'No Validated Results Available' : 'कुनै प्रमाणीकृत नतिजा उपलब्ध छैन'}
            </h3>
            <p className="text-[11px] text-slate-400 mt-1 max-w-sm mx-auto">
              {language === 'en'
                ? 'The Situation-Report Copilot requires validated spatial outputs before generating reports. Every numerical claim is verified against computed data.'
                : 'स्थिति प्रतिवेदन तयार गर्न प्रमाणित भौगोलिक परिणामहरू आवश्यक पर्दछ। प्रत्येक संख्यात्मक विवरण गणना गरिएको तथ्याङ्कबाट प्रमाणित गरिन्छ।'}
            </p>
          </div>

          {/* Interactive Q&A Input (Awaiting Pipeline) */}
          <div className="space-y-2">
            <label className="block text-xs font-medium text-slate-400">
              {language === 'en' ? 'Ask Geospatial Copilot:' : 'भौगोलिक कोपाइलटलाई सोध्नुहोस्:'}
            </label>
            <div className="flex items-center space-x-2">
              <input
                type="text"
                disabled
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder={
                  language === 'en'
                    ? 'e.g., Which river crossing was impacted along Highway F021?'
                    : 'जस्तै: राजमार्ग F021 मा कुन पुल प्रभावित भएको छ?'
                }
                className="flex-1 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-400 cursor-not-allowed placeholder:text-slate-600"
              />
              <button
                disabled
                className="p-2 bg-slate-800 text-slate-600 rounded-lg cursor-not-allowed border border-slate-700"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
            <p className="text-[10px] text-slate-400">
              {language === 'en'
                ? 'Strict Grounding: The Copilot rejects unsupported numerical claims and distinguishes candidate flood extent from confirmed damage.'
                : 'कडा प्रमाणीकरण: कोपाइलटले अप्रमाणित संख्यात्मक दाबीहरू अस्वीकार गर्दछ।'}
            </p>
          </div>
        </div>
      ) : null}
    </div>
  );
};
