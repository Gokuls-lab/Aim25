

import { useState, useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Send, Download, Sparkles, Upload, FileSpreadsheet } from 'lucide-react';
import ResearchProgress from './components/ResearchProgress';
import Dashboard from './components/Dashboard';
import GraphView from './components/GraphView';

function App() {
  const [mode, setMode] = useState('single'); // 'single' | 'bulk'
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState('idle'); // idle, working, done
  const [logs, setLogs] = useState([]);
  const [result, setResult] = useState(null);
  const [pdfUrl, setPdfUrl] = useState(null);
  const [excelUrl, setExcelUrl] = useState(null);
  const [bulkProgress, setBulkProgress] = useState({ current: 0, total: 0 });
  const ws = useRef(null);
  const scrollRef = useRef(null);

  /* New State for Bulk Confirmation */
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [confirmData, setConfirmData] = useState({ count: 0, filename: "" });

  const startResearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setStatus('working');
    setLogs(["Initializing connection..."]);
    setResult(null);

    const company = query.trim();
    ws.current = new WebSocket(`ws://localhost:8000/ws/research/${company}`);

    ws.current.onopen = () => setLogs(p => [...p, "Connected to Atlas Core."]);

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "log") setLogs(prev => [...prev, data.content]);

      if (data.type === "result") {
        setResult(data.profile);
        setPdfUrl(data.pdf_url);
        setStatus('done');
        ws.current.close();
      }
    };
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Don't set status to 'working' yet, just 'analyzing'
    setLogs([`Uploading ${file.name}...`]);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch('http://localhost:8000/upload_csv', {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      // Init WebSocket and ask for analysis
      initBulkConnection(data.filename);
    } catch (err) {
      setLogs(p => [...p, `Error uploading: ${err.message}`]);
    }
  };

  const initBulkConnection = (filename) => {
    ws.current = new WebSocket(`ws://localhost:8000/ws/bulk`);

    ws.current.onopen = () => {
      setLogs(p => [...p, "Connected. Analyzing CSV structure..."]);
      // Step 1: Request Analysis
      ws.current.send(JSON.stringify({ type: "analyze_file", filename }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "analysis_result") {
        // Step 2: Show Confirmation Popup
        setConfirmData({ count: data.count, filename: data.filename });
        setShowConfirmModal(true);
      }

      if (data.type === "log") setLogs(prev => [...prev, data.content]);

      if (data.type === "progress") {
        setBulkProgress({ current: data.current, total: data.total });
      }

      if (data.type === "bulk_result") {
        setExcelUrl(data.excel_url);
        setStatus('done');
        ws.current.close();
        setLogs(p => [...p, `✅ Bulk processing complete. Processed ${data.count} profiles.`]);
      }

      if (data.type === "error") {
        setLogs(p => [...p, `❌ Error: ${data.content}`]);
        // If error during analysis, might need to reset
      }
    };
  };

  const confirmBulkStart = () => {
    setShowConfirmModal(false);
    setStatus('working'); // Now we switch UI to working mode
    setLogs(p => [...p, `Confirmed. Starting processing for ${confirmData.count} domains...`]);

    // Step 3: Send Start Signal
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "confirm_start", filename: confirmData.filename }));
    }
  };

  const cancelBulk = () => {
    setShowConfirmModal(false);
    setLogs([]);
    if (ws.current) ws.current.close();
  };

  // Auto-scroll to bottom of chat
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [status, logs, result]);

  return (
    <div className="bg-[#050505] min-h-screen text-white font-sans flex flex-col relative">

      {/* CONFIRMATION MODAL */}
      <AnimatePresence>
        {showConfirmModal && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
          >
            <motion.div
              initial={{ scale: 0.9 }} animate={{ scale: 1 }}
              className="bg-[#111] border border-white/10 p-8 rounded-2xl max-w-md w-full shadow-2xl space-y-6"
            >
              <div className="flex items-center gap-3 text-blue-400 mb-2">
                <Sparkles className="w-6 h-6" />
                <h3 className="text-xl font-bold text-white">Ready to Research?</h3>
              </div>

              <div className="space-y-2">
                <p className="text-gray-300">We found <span className="text-white font-bold text-lg">{confirmData.count} valid domains</span> in your CSV.</p>
                <p className="text-xs text-gray-500">Blank rows have been automatically filtered out.</p>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={cancelBulk}
                  className="flex-1 px-4 py-3 rounded-xl bg-white/5 hover:bg-white/10 text-gray-400 font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={confirmBulkStart}
                  className="flex-1 px-4 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-bold transition-colors shadow-lg shadow-blue-900/20"
                >
                  Start Research
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 1. TOP BAR */}
      <div className="h-14 border-b border-white/5 flex items-center px-6 justify-between bg-[#0a0a0a]/50 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-blue-400" />
          <span className="font-semibold text-sm tracking-wide">ATLAS <span className="text-gray-600 font-normal">/ DEEP RESEARCH</span></span>
        </div>
        <div className="flex gap-4 text-xs font-mono">
          <button onClick={() => setMode('single')} className={`${mode === 'single' ? 'text-blue-400' : 'text-gray-600'} hover:text-white transition-colors`}>SINGLE_TARGET</button>
          <button onClick={() => setMode('bulk')} className={`${mode === 'bulk' ? 'text-blue-400' : 'text-gray-600'} hover:text-white transition-colors`}>BULK_UPLOAD</button>
        </div>
      </div>

      {/* 2. MAIN CONTENT AREA */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 relative">
        <div className="max-w-4xl mx-auto min-h-[500px] flex flex-col justify-end pb-24">

          <AnimatePresence mode="wait">
            {/* IDLE STATE */}
            {status === 'idle' && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="text-center py-20 space-y-6"
              >
                <h1 className="text-4xl md:text-5xl font-bold bg-gradient-to-br from-white to-gray-600 bg-clip-text text-transparent">
                  {mode === 'single' ? "What company are you analyzing?" : "Bulk Research Pipeline"}
                </h1>
                <p className="text-gray-400">
                  {mode === 'single'
                    ? "Atlas performs autonomous deep dives into corporate entities."
                    : "Upload a CSV with a 'domain' column to generate a comprehensive Excel report."}
                </p>

                {mode === 'bulk' && (
                  <div className="flex justify-center mt-8">
                    <label className="cursor-pointer btn-primary px-8 py-4 bg-blue-600/20 hover:bg-blue-600/30 border border-blue-500/50 rounded-xl flex items-center gap-3 transition-all">
                      <Upload className="w-5 h-5 text-blue-400" />
                      <span className="text-blue-100 font-medium">Upload CSV File</span>
                      <input type="file" accept=".csv" className="hidden" onChange={handleFileUpload} />
                    </label>
                  </div>
                )}
              </motion.div>
            )}

            {/* WORKING STATE */}
            {status === 'working' && (
              <motion.div
                initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                className="w-full"
              >
                {mode === 'bulk' && bulkProgress.total > 0 && (
                  <div className="mb-8 p-6 bg-[#111] rounded-xl border border-white/10">
                    <div className="flex justify-between mb-2 text-sm text-gray-400">
                      <span>Progress</span>
                      <span>{bulkProgress.current} / {bulkProgress.total}</span>
                    </div>
                    <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-blue-500 transition-all duration-500"
                        style={{ width: `${(bulkProgress.current / bulkProgress.total) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
                <ResearchProgress logs={logs} />
              </motion.div>
            )}

            {/* RESULT STATE */}
            {status === 'done' && (
              <motion.div
                initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                className="space-y-8"
              >
                {mode === 'single' && result && (
                  <>
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-2xl font-bold">Research Report: {result.name}</h2>
                        <p className="text-gray-400 text-sm">Generated by Atlas Agent</p>
                      </div>
                      {pdfUrl && (
                        <a href={pdfUrl} download target="_blank" className="btn-primary flex items-center gap-2 text-sm py-2 px-4 bg-white text-black rounded-lg hover:bg-gray-200">
                          <Download className="w-4 h-4" /> Download JSON/PDF
                        </a>
                      )}
                    </div>
                    <div className="w-full">
                      <GraphView data={result} />
                    </div>
                    <Dashboard data={result} />
                  </>
                )}

                {mode === 'bulk' && excelUrl && (
                  <div className="text-center py-20 bg-[#111] rounded-2xl border border-white/10">
                    <FileSpreadsheet className="w-16 h-16 text-green-500 mx-auto mb-6" />
                    <h2 className="text-3xl font-bold mb-4">Bulk Report Ready</h2>
                    <p className="text-gray-400 mb-8">Successfully processed {bulkProgress.current} domains.</p>
                    <a href={excelUrl} download className="inline-flex items-center gap-3 px-8 py-3 bg-green-600 text-white rounded-xl hover:bg-green-500 font-medium transition-colors">
                      <Download className="w-5 h-5" /> Download Excel Report
                    </a>
                    <button
                      onClick={() => { setStatus('idle'); setLogs([]); setBulkProgress({ current: 0, total: 0 }); }}
                      className="block mx-auto mt-6 text-sm text-gray-500 hover:text-white"
                    >
                      Start New Batch
                    </button>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>
          <div ref={scrollRef} />
        </div>
      </div>

      {/* 3. INPUT AREA (Fixed Bottom) - ONLY FOR SINGLE MODE */}
      {mode === 'single' && (
        <div className="p-6 fixed bottom-0 left-0 w-full bg-gradient-to-t from-[#050505] via-[#050505] to-transparent z-40">
          <div className="max-w-3xl mx-auto relative group">
            <form onSubmit={startResearch}>
              <input
                type="text"
                disabled={status === 'working'}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder={status === 'working' ? "Analysis in progress..." : "Ask Atlas to research a company..."}
                className="w-full bg-[#151515] border border-white/10 rounded-2xl py-4 pl-6 pr-14 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-blue-500/50 shadow-2xl transition-all"
              />
              <button
                type="submit"
                disabled={status === 'working' || !query}
                className="absolute right-3 top-3 p-2 bg-white text-black rounded-xl hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <Send className="w-4 h-4" />
              </button>
            </form>
            <div className="text-center mt-3 text-xs text-gray-600">
              Atlas Agent can make mistakes. Please verify important corporate data.
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;
