import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { TrendingUp, RefreshCw, Zap, ArrowRight, Loader } from 'lucide-react';

export default function TrendsDashboard({ brands }) {
    const [trends, setTrends] = useState([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [selectedTrend, setSelectedTrend] = useState(null);
    const [selectedBrandId, setSelectedBrandId] = useState('');
    const [generating, setGenerating] = useState(false);
    const [generatedContent, setGeneratedContent] = useState(null);

    useEffect(() => {
        fetchTrends();
    }, []);

    const fetchTrends = async () => {
        try {
            const token = localStorage.getItem('token');
            const res = await fetch('/api/trends', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const data = await res.json();
            setTrends(data);
        } catch (error) {
            console.error("Failed to fetch trends:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleRefreshTrends = async () => {
        setRefreshing(true);
        try {
            const token = localStorage.getItem('token');
            await fetch('/api/trends/refresh', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            await fetchTrends();
        } catch (error) {
            console.error("Failed to refresh trends:", error);
        } finally {
            setRefreshing(false);
        }
    };

    const handleGenerate = async () => {
        if (!selectedBrandId || !selectedTrend) return;

        setGenerating(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`/api/generate/${selectedBrandId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    trend: selectedTrend.topic,
                    trend_id: selectedTrend.id
                })
            });

            if (res.ok) {
                const data = await res.json();
                setGeneratedContent(data);
                // Reset selection
                setSelectedTrend(null);
                setSelectedBrandId('');
                alert("Content generated successfully! Check your brand dashboard.");
            } else {
                alert("Generation failed. Please try again.");
            }
        } catch (error) {
            console.error("Generation error:", error);
        } finally {
            setGenerating(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading trends...</div>;

    return (
        <div className="space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                        <TrendingUp className="text-indigo-600" />
                        Trending Now
                    </h2>
                    <p className="text-gray-500 mt-1">Real-time trends from Google & Twitter. Pick one to generate content.</p>
                </div>
                <button
                    onClick={handleRefreshTrends}
                    disabled={refreshing}
                    className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
                >
                    <RefreshCw size={16} className={refreshing ? "animate-spin" : ""} />
                    {refreshing ? 'Refreshing...' : 'Refresh Trends'}
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {trends.map((trend, index) => (
                    <motion.div
                        key={trend.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: index * 0.05 }}
                        className={`bg-white rounded-xl shadow-sm border p-6 cursor-pointer transition-all ${selectedTrend?.id === trend.id
                                ? 'border-indigo-500 ring-2 ring-indigo-100'
                                : 'border-gray-100 hover:border-indigo-200 hover:shadow-md'
                            }`}
                        onClick={() => setSelectedTrend(trend)}
                    >
                        <div className="flex justify-between items-start mb-3">
                            <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-2 py-1 rounded-md uppercase tracking-wide">
                                {trend.source}
                            </span>
                            <span className="text-xs text-gray-400">
                                {new Date(trend.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                        </div>
                        <h3 className="text-lg font-bold text-gray-900 mb-2 line-clamp-2">
                            {trend.topic}
                        </h3>
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <TrendingUp size={14} />
                            <span>{trend.volume || 'High Volume'}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Generation Modal / Bottom Sheet */}
            {selectedTrend && (
                <div className="fixed inset-0 bg-black/50 flex items-end sm:items-center justify-center z-50 p-4">
                    <motion.div
                        initial={{ y: "100%" }}
                        animate={{ y: 0 }}
                        className="bg-white w-full max-w-lg rounded-t-2xl sm:rounded-2xl p-6 shadow-2xl"
                    >
                        <h3 className="text-xl font-bold text-gray-900 mb-4">Generate Content</h3>
                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Selected Trend</label>
                            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200 font-medium text-gray-900">
                                {selectedTrend.topic}
                            </div>
                        </div>

                        <div className="mb-6">
                            <label className="block text-sm font-medium text-gray-700 mb-2">Choose Brand</label>
                            <select
                                value={selectedBrandId}
                                onChange={(e) => setSelectedBrandId(e.target.value)}
                                className="w-full p-3 rounded-lg border border-gray-200 focus:ring-2 focus:ring-indigo-500 outline-none"
                            >
                                <option value="">Select a brand...</option>
                                {brands.map(brand => (
                                    <option key={brand.id} value={brand.id}>{brand.name}</option>
                                ))}
                            </select>
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setSelectedTrend(null)}
                                className="flex-1 py-3 text-gray-600 font-medium hover:bg-gray-50 rounded-xl transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleGenerate}
                                disabled={!selectedBrandId || generating}
                                className="flex-1 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-700 transition-colors flex items-center justify-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed"
                            >
                                {generating ? (
                                    <>
                                        <Loader className="animate-spin" size={20} /> Generating...
                                    </>
                                ) : (
                                    <>
                                        <Zap size={20} /> Generate
                                    </>
                                )}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
}
