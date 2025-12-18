import { motion, AnimatePresence } from 'framer-motion';
import { Search, Globe, ExternalLink, Zap, Database, FileText, CheckCircle2, ChevronRight } from 'lucide-react';
import { useEffect, useState, useRef } from 'react';

// Parse log entry to determine type and extract data
const parseLogEntry = (log) => {
    // G-Search pattern
    if (log.startsWith("G-Search:")) {
        const query = log.replace("G-Search:", "").trim().replace(/^['"]|['"]$/g, '');
        return { type: 'g-search', query, icon: Search, color: '#22c55e', bgColor: 'rgba(34, 197, 94, 0.1)', label: 'Google Search' };
    }
    
    // D-Search pattern (DuckDuckGo or another search)
    if (log.startsWith("D-Search:")) {
        const query = log.replace("D-Search:", "").trim().replace(/^['"]|['"]$/g, '');
        return { type: 'd-search', query, icon: Database, color: '#f59e0b', bgColor: 'rgba(245, 158, 11, 0.1)', label: 'Deep Search' };
    }
    
    // Surfing pattern
    if (log.startsWith("📄 Surfing:") || log.includes("Surfing:")) {
        const url = log.replace("📄 Surfing:", "").replace("Surfing:", "").trim();
        return { type: 'surfing', url, icon: Globe, color: '#3b82f6', bgColor: 'rgba(59, 130, 246, 0.1)', label: 'Browsing' };
    }
    
    // Reading pattern
    if (log.includes("Reading") || log.includes("Extracting")) {
        return { type: 'processing', text: log, icon: FileText, color: '#a855f7', bgColor: 'rgba(168, 85, 247, 0.1)', label: 'Processing' };
    }
    
    // Completed/Success pattern
    if (log.includes("✅") || log.includes("complete") || log.includes("Complete")) {
        return { type: 'success', text: log, icon: CheckCircle2, color: '#10b981', bgColor: 'rgba(16, 185, 129, 0.1)', label: 'Complete' };
    }
    
    // Default pattern
    return { type: 'default', text: log, icon: Zap, color: '#6b7280', bgColor: 'rgba(107, 114, 128, 0.1)', label: 'Activity' };
};

// Truncate URL for display
const truncateUrl = (url, maxLength = 45) => {
    if (!url) return '';
    try {
        const urlObj = new URL(url);
        const displayUrl = urlObj.hostname + urlObj.pathname;
        return displayUrl.length > maxLength ? displayUrl.slice(0, maxLength) + '...' : displayUrl;
    } catch {
        return url.length > maxLength ? url.slice(0, maxLength) + '...' : url;
    }
};

// Individual Log Entry Component
const LogEntry = ({ entry, index, isLatest }) => {
    const parsed = parseLogEntry(entry);
    const Icon = parsed.icon;
    
    return (
        <motion.div
            initial={{ opacity: 0, x: -20, scale: 0.95 }}
            animate={{ 
                opacity: isLatest ? 1 : 0.7, 
                x: 0, 
                scale: 1,
            }}
            exit={{ opacity: 0, x: 20, scale: 0.95 }}
            transition={{ 
                duration: 0.4, 
                delay: 0.05,
                ease: [0.25, 0.46, 0.45, 0.94] 
            }}
            className={`relative group ${isLatest ? 'z-10' : 'z-0'}`}
        >
            {/* Connection Line */}
            {index > 0 && (
                <div className="absolute left-5 -top-3 w-0.5 h-3 bg-gradient-to-b from-transparent via-white/10 to-white/5" />
            )}
            
            <div 
                className={`relative flex items-start gap-4 p-4 rounded-xl border transition-all duration-300 ${
                    isLatest 
                        ? 'bg-white/[0.03] border-white/15 shadow-lg shadow-black/20' 
                        : 'bg-transparent border-transparent hover:bg-white/[0.02] hover:border-white/10'
                }`}
                style={{
                    background: isLatest ? parsed.bgColor : 'transparent',
                    borderColor: isLatest ? `${parsed.color}30` : 'transparent',
                }}
            >
                {/* Icon Container */}
                <div 
                    className="relative flex-shrink-0"
                >
                    <motion.div
                        animate={isLatest ? { 
                            boxShadow: [
                                `0 0 0 0 ${parsed.color}40`,
                                `0 0 0 8px ${parsed.color}00`,
                            ]
                        } : {}}
                        transition={{ duration: 1.5, repeat: isLatest ? Infinity : 0 }}
                        className="w-10 h-10 rounded-xl flex items-center justify-center"
                        style={{ 
                            backgroundColor: `${parsed.color}20`,
                            border: `1px solid ${parsed.color}30`
                        }}
                    >
                        <Icon 
                            className="w-5 h-5" 
                            style={{ color: parsed.color }}
                        />
                    </motion.div>
                    
                    {/* Active indicator dot */}
                    {isLatest && (
                        <motion.div
                            animate={{ scale: [1, 1.2, 1], opacity: [1, 0.7, 1] }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                            className="absolute -top-0.5 -right-0.5 w-3 h-3 rounded-full"
                            style={{ backgroundColor: parsed.color }}
                        />
                    )}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0 pt-1">
                    {/* Label */}
                    <div className="flex items-center gap-2 mb-1">
                        <span 
                            className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                            style={{ 
                                color: parsed.color, 
                                backgroundColor: `${parsed.color}20` 
                            }}
                        >
                            {parsed.label}
                        </span>
                        {isLatest && (
                            <motion.span
                                animate={{ opacity: [1, 0.5, 1] }}
                                transition={{ duration: 1, repeat: Infinity }}
                                className="text-[10px] text-gray-500"
                            >
                                LIVE
                            </motion.span>
                        )}
                    </div>
                    
                    {/* Query/URL/Text */}
                    {parsed.type === 'g-search' || parsed.type === 'd-search' ? (
                        <div className="font-mono text-sm text-white/90">
                            <span className="text-gray-500">"</span>
                            {parsed.query}
                            <span className="text-gray-500">"</span>
                        </div>
                    ) : parsed.type === 'surfing' ? (
                        <div className="flex items-center gap-2">
                            <span className="font-mono text-sm text-blue-300 truncate">
                                {truncateUrl(parsed.url)}
                            </span>
                            <a 
                                href={parsed.url} 
                                target="_blank" 
                                rel="noopener noreferrer"
                                className="text-gray-500 hover:text-blue-400 transition-colors opacity-0 group-hover:opacity-100"
                            >
                                <ExternalLink className="w-3 h-3" />
                            </a>
                        </div>
                    ) : (
                        <div className="text-sm text-gray-300">
                            {parsed.text}
                        </div>
                    )}
                </div>
                
                {/* Chevron indicator for latest */}
                {isLatest && (
                    <motion.div
                        animate={{ x: [0, 4, 0] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="flex-shrink-0 pt-2"
                    >
                        <ChevronRight className="w-4 h-4 text-gray-600" />
                    </motion.div>
                )}
            </div>
        </motion.div>
    );
};

// Stats bar showing counts
const StatsBar = ({ logs }) => {
    const stats = logs.reduce((acc, log) => {
        const parsed = parseLogEntry(log);
        acc[parsed.type] = (acc[parsed.type] || 0) + 1;
        return acc;
    }, {});
    
    const statItems = [
        { type: 'g-search', label: 'Searches', color: '#22c55e', icon: Search },
        { type: 'd-search', label: 'Deep', color: '#f59e0b', icon: Database },
        { type: 'surfing', label: 'Pages', color: '#3b82f6', icon: Globe },
    ];
    
    return (
        <div className="flex items-center gap-4 p-3 bg-white/[0.02] rounded-xl border border-white/5 mb-4">
            {statItems.map(item => (
                <div 
                    key={item.type}
                    className="flex items-center gap-2"
                >
                    <item.icon className="w-3.5 h-3.5" style={{ color: item.color }} />
                    <span className="text-xs text-gray-400">{item.label}</span>
                    <motion.span 
                        key={stats[item.type] || 0}
                        initial={{ scale: 1.3, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="text-xs font-bold tabular-nums"
                        style={{ color: item.color }}
                    >
                        {stats[item.type] || 0}
                    </motion.span>
                </div>
            ))}
        </div>
    );
};

// Main Component
export default function LiveActivityLog({ logs }) {
    const scrollContainerRef = useRef(null);
    const [isAutoScroll, setIsAutoScroll] = useState(true);
    
    // Auto-scroll to bottom when new logs arrive
    useEffect(() => {
        if (isAutoScroll && scrollContainerRef.current) {
            scrollContainerRef.current.scrollTo({
                top: scrollContainerRef.current.scrollHeight,
                behavior: 'smooth'
            });
        }
    }, [logs, isAutoScroll]);
    
    // Handle scroll to detect if user scrolled up
    const handleScroll = (e) => {
        const { scrollTop, scrollHeight, clientHeight } = e.target;
        const isAtBottom = scrollHeight - scrollTop - clientHeight < 50;
        setIsAutoScroll(isAtBottom);
    };

    // Filter out empty or initialization logs
    const filteredLogs = logs.filter(log => 
        log && 
        log.trim() !== '' && 
        !log.includes('Initializing') && 
        !log.includes('Connected')
    );
    
    return (
        <div className="w-full">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <div className="relative">
                        <motion.div
                            animate={{ 
                                boxShadow: [
                                    '0 0 0 0 rgba(59, 130, 246, 0.4)',
                                    '0 0 0 10px rgba(59, 130, 246, 0)',
                                ]
                            }}
                            transition={{ duration: 2, repeat: Infinity }}
                            className="w-3 h-3 bg-blue-500 rounded-full"
                        />
                    </div>
                    <h3 className="text-sm font-semibold text-white">Research Activity</h3>
                    <span className="text-xs text-gray-500 font-mono">
                        {filteredLogs.length} events
                    </span>
                </div>
                
                {!isAutoScroll && (
                    <motion.button
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        onClick={() => setIsAutoScroll(true)}
                        className="text-xs text-blue-400 hover:text-blue-300 transition-colors flex items-center gap-1"
                    >
                        <span>Jump to latest</span>
                        <ChevronRight className="w-3 h-3 rotate-90" />
                    </motion.button>
                )}
            </div>
            
            {/* Stats Bar */}
            {filteredLogs.length > 0 && <StatsBar logs={filteredLogs} />}
            
            {/* Log Container */}
            <div 
                ref={scrollContainerRef}
                onScroll={handleScroll}
                className="max-h-[400px] overflow-y-auto pr-2 space-y-1 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent"
                style={{
                    maskImage: 'linear-gradient(to bottom, transparent 0%, black 5%, black 95%, transparent 100%)'
                }}
            >
                <AnimatePresence mode="popLayout">
                    {filteredLogs.map((log, index) => (
                        <LogEntry 
                            key={`${index}-${log}`}
                            entry={log}
                            index={index}
                            isLatest={index === filteredLogs.length - 1}
                        />
                    ))}
                </AnimatePresence>
                
                {/* Empty state */}
                {filteredLogs.length === 0 && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-center py-12 text-gray-500"
                    >
                        <Globe className="w-8 h-8 mx-auto mb-3 opacity-50" />
                        <p className="text-sm">Waiting for research activity...</p>
                    </motion.div>
                )}
            </div>
            
            {/* Bottom gradient fade */}
            <div className="h-4 bg-gradient-to-t from-[#0a0a0a] to-transparent -mt-4 relative z-10 pointer-events-none" />
        </div>
    );
}
