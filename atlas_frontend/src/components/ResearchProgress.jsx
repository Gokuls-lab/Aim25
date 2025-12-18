import { motion } from 'framer-motion';
import { Loader2, Globe, Brain, CheckCircle2, Search } from 'lucide-react';
import LiveActivityLog from './LiveActivityLog';

export default function ResearchProgress({ logs }) {
    // We parse the logs to find the "Current Action"
    const lastLog = logs[logs.length - 1] || "";

    // Determine phase based on log keywords
    let phase = "initializing";
    if (lastLog.includes("Researching") || lastLog.includes("G-Search") || lastLog.includes("D-Search")) phase = "searching";
    if (lastLog.includes("Reading") || lastLog.includes("Surfing")) phase = "reading";
    if (lastLog.includes("Extracting")) phase = "thinking";
    if (lastLog.includes("Graph") || lastLog.includes("✅")) phase = "finalizing";

    const steps = [
        { id: "searching", label: "Searching", icon: Search },
        { id: "reading", label: "Browsing", icon: Globe },
        { id: "thinking", label: "Extracting", icon: Brain },
        { id: "finalizing", label: "Finalizing", icon: CheckCircle2 },
    ];

    const getStepStatus = (stepId) => {
        const stepOrder = ["searching", "reading", "thinking", "finalizing"];
        const currentIndex = stepOrder.indexOf(phase);
        const stepIndex = stepOrder.indexOf(stepId);

        if (stepIndex < currentIndex) return "completed";
        if (stepIndex === currentIndex) return "active";
        return "pending";
    };

    return (
        <div className="w-full max-w-3xl mx-auto space-y-6">
            {/* Header Card */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="glass-panel p-6"
            >
                <div className="flex items-center gap-4 mb-6">
                    <div className="relative">
                        <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center">
                            <Loader2 className="w-6 h-6 text-blue-400 animate-spin" />
                        </div>
                        <motion.div
                            animate={{ scale: [1, 1.4, 1], opacity: [0.5, 0.2, 0.5] }}
                            transition={{ duration: 2, repeat: Infinity }}
                            className="absolute inset-0 bg-blue-500/30 rounded-full blur-xl"
                        />
                    </div>
                    <div>
                        <h3 className="text-xl font-semibold text-white">Deep Research in Progress</h3>
                        <p className="text-gray-400 text-sm">Atlas is autonomously navigating the web...</p>
                    </div>
                </div>

                {/* Steps Visualizer */}
                <div className="flex items-center justify-between">
                    {steps.map((step, index) => {
                        const status = getStepStatus(step.id);
                        const Icon = step.icon;

                        return (
                            <div key={step.id} className="flex items-center">
                                <div className={`flex flex-col items-center gap-2 transition-all duration-500`}>
                                    <motion.div
                                        animate={status === "active" ? {
                                            scale: [1, 1.1, 1],
                                            boxShadow: [
                                                '0 0 0 0 rgba(59, 130, 246, 0.4)',
                                                '0 0 0 8px rgba(59, 130, 246, 0)',
                                            ]
                                        } : {}}
                                        transition={{ duration: 1.5, repeat: status === "active" ? Infinity : 0 }}
                                        className={`w-10 h-10 rounded-xl flex items-center justify-center border transition-all duration-300 ${status === "completed"
                                                ? "bg-green-500/20 border-green-500/50 text-green-400"
                                                : status === "active"
                                                    ? "bg-blue-500/20 border-blue-500/50 text-blue-400"
                                                    : "bg-white/5 border-white/10 text-gray-600"
                                            }`}
                                    >
                                        <Icon className="w-4 h-4" />
                                    </motion.div>
                                    <span className={`text-[10px] uppercase tracking-wider font-medium transition-colors duration-300 ${status === "completed"
                                            ? "text-green-400"
                                            : status === "active"
                                                ? "text-white"
                                                : "text-gray-600"
                                        }`}>
                                        {step.label}
                                    </span>
                                </div>

                                {/* Connector Line */}
                                {index < steps.length - 1 && (
                                    <div className="w-12 h-0.5 mx-2 rounded-full overflow-hidden bg-white/5">
                                        <motion.div
                                            className="h-full bg-gradient-to-r from-blue-500 to-blue-400"
                                            initial={{ width: "0%" }}
                                            animate={{
                                                width: getStepStatus(steps[index + 1].id) !== "pending" ? "100%" : "0%"
                                            }}
                                            transition={{ duration: 0.5 }}
                                        />
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </motion.div>

            {/* Live Activity Log */}
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="glass-panel p-6"
            >
                <LiveActivityLog logs={logs} />
            </motion.div>
        </div>
    );
}
