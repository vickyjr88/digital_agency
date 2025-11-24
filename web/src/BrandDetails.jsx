import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowLeft, Edit2, RefreshCw, Settings, TrendingUp, Loader, Zap, Eye, Copy, Check } from 'lucide-react';

export default function BrandDetails() {
    const { id } = useParams();
    const navigate = useNavigate();
    const [brand, setBrand] = useState(null);
    const [content, setContent] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [copiedId, setCopiedId] = useState(null);

    const handleCopy = (text, id) => {
        navigator.clipboard.writeText(text);
        setCopiedId(id);
        setTimeout(() => setCopiedId(null), 2000);
    };

    // Trend Modal State
    const [showTrendModal, setShowTrendModal] = useState(false);
    const [trends, setTrends] = useState([]);
    const [loadingTrends, setLoadingTrends] = useState(false);
    const [selectedTrend, setSelectedTrend] = useState(null);

    useEffect(() => {
        fetchBrandData();
    }, [id]);

    const fetchBrandData = async () => {
        try {
            const token = localStorage.getItem('token');
            // Fetch Brand Details
            const brandRes = await fetch(`/api/brands/${id}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!brandRes.ok) throw new Error('Failed to fetch brand');
            const brandData = await brandRes.json();
            setBrand(brandData);

            // Fetch Brand Content
            const contentRes = await fetch(`/api/brands/${id}/content`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (contentRes.ok) {
                const contentData = await contentRes.json();
                setContent(contentData);
            }
        } catch (error) {
            console.error("Error:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleOpenGenerateModal = async () => {
        setShowTrendModal(true);
        setLoadingTrends(true);
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
            setLoadingTrends(false);
        }
    };

    const handleGenerate = async () => {
        if (!selectedTrend) return;

        setGenerating(true);
        try {
            const token = localStorage.getItem('token');
            const res = await fetch(`/api/generate/${id}`, {
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
                setShowTrendModal(false);
                setSelectedTrend(null);
                fetchBrandData(); // Refresh content list
                alert("Content generated successfully!");
            } else {
                alert("Generation failed. Please try again.");
            }
        } catch (error) {
            console.error("Generation failed:", error);
        } finally {
            setGenerating(false);
        }
    };

    if (loading) return <div className="p-8 text-center">Loading brand...</div>;
    if (!brand) return <div className="p-8 text-center">Brand not found</div>;

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <div className="max-w-6xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center gap-2 text-gray-500 hover:text-gray-900 mb-4 transition-colors"
                    >
                        <ArrowLeft size={18} /> Back to Dashboard
                    </button>

                    <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex justify-between items-start">
                        <div className="flex gap-4">
                            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-2xl shadow-md">
                                {brand.name[0]}
                            </div>
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">{brand.name}</h1>
                                <p className="text-gray-500 mt-1">{brand.industry} • {brand.voice} Voice</p>
                                <div className="flex gap-2 mt-3">
                                    {brand.hashtags?.map(tag => (
                                        <span key={tag} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded-md">
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-2">
                            <button
                                onClick={handleOpenGenerateModal}
                                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm"
                            >
                                <RefreshCw size={18} />
                                Generate New Content
                            </button>
                            <button className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded-lg transition-colors">
                                <Settings size={20} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Content List */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {content.map((item, index) => (
                        <motion.div
                            key={item.id}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden border border-gray-100 flex flex-col"
                        >
                            <div className="p-5 border-b border-gray-50 bg-gray-50/30">
                                <div className="flex justify-between items-start mb-2">
                                    <span className={`px-2 py-0.5 text-xs font-bold uppercase tracking-wide rounded-full ${item.status === 'approved' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                                        }`}>
                                        {item.status || 'Pending'}
                                    </span>
                                    <span className="text-xs text-gray-400 font-mono">
                                        {new Date(item.generated_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <h3 className="font-bold text-gray-900 line-clamp-2 text-lg leading-tight mt-2">
                                    {item.trend}
                                </h3>
                            </div>

                            <div className="p-5 space-y-4 flex-1 flex flex-col">
                                <div className="flex-1">
                                    <p className="text-sm text-gray-600 line-clamp-4 leading-relaxed">
                                        {item.tweet || 'No tweet content.'}
                                    </p>
                                </div>

                                <div className="flex gap-2 pt-4 mt-auto border-t border-gray-50">
                                    <button
                                        onClick={() => navigate(`/view/${item.id}`, { state: { item } })}
                                        className="p-2 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                        title="View Details"
                                    >
                                        <Eye size={18} />
                                    </button>
                                    <button
                                        onClick={() => handleCopy(item.tweet, item.id)}
                                        className="p-2 text-gray-500 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                                        title="Copy Tweet"
                                    >
                                        {copiedId === item.id ? <Check size={18} className="text-green-600" /> : <Copy size={18} />}
                                    </button>
                                    <button
                                        onClick={() => navigate(`/edit/${item.id}`, { state: { item } })}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-indigo-50 text-indigo-600 rounded-lg hover:bg-indigo-100 transition-colors text-sm font-semibold"
                                    >
                                        <Edit2 size={16} /> Edit
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>

                {content.length === 0 && (
                    <div className="text-center py-12 text-gray-500">
                        No content generated yet. Click "Generate New Content" to start.
                    </div>
                )}
            </div>

            {/* Trend Selection Modal */}
            {showTrendModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <motion.div
                        initial={{ scale: 0.95, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        className="bg-white w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh]"
                    >
                        <div className="p-6 border-b border-gray-100 flex justify-between items-center bg-gray-50">
                            <h3 className="text-xl font-bold text-gray-900">Select a Trend</h3>
                            <button onClick={() => setShowTrendModal(false)} className="text-gray-400 hover:text-gray-600">
                                <span className="text-2xl">&times;</span>
                            </button>
                        </div>

                        <div className="p-6 overflow-y-auto flex-1">
                            {loadingTrends ? (
                                <div className="text-center py-8">
                                    <Loader className="animate-spin mx-auto text-indigo-600" size={32} />
                                    <p className="mt-2 text-gray-500">Fetching latest trends...</p>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                    {trends.map(trend => (
                                        <div
                                            key={trend.id}
                                            onClick={() => setSelectedTrend(trend)}
                                            className={`p-4 rounded-xl border cursor-pointer transition-all ${selectedTrend?.id === trend.id
                                                ? 'border-indigo-500 bg-indigo-50 ring-1 ring-indigo-500'
                                                : 'border-gray-200 hover:border-indigo-300 hover:bg-gray-50'
                                                }`}
                                        >
                                            <div className="flex justify-between items-start mb-2">
                                                <span className="text-xs font-bold text-indigo-600 uppercase">{trend.source}</span>
                                                <span className="text-xs text-gray-400">{trend.volume}</span>
                                            </div>
                                            <h4 className="font-bold text-gray-900">{trend.topic}</h4>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="p-6 border-t border-gray-100 bg-gray-50 flex justify-end gap-3">
                            <button
                                onClick={() => setShowTrendModal(false)}
                                className="px-6 py-2 text-gray-600 font-medium hover:bg-gray-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleGenerate}
                                disabled={!selectedTrend || generating}
                                className="px-6 py-2 bg-indigo-600 text-white font-bold rounded-lg hover:bg-indigo-700 transition-colors flex items-center gap-2 disabled:opacity-70"
                            >
                                {generating ? <Loader className="animate-spin" size={18} /> : <Zap size={18} />}
                                {generating ? 'Generating...' : 'Generate Content'}
                            </button>
                        </div>
                    </motion.div>
                </div>
            )}
        </div>
    );
}
