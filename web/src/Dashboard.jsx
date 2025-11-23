import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Edit2, Copy, Eye, RefreshCw, LogOut } from 'lucide-react';

export default function Dashboard() {
    const [content, setContent] = useState([]);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetchContent();
    }, []);

    const fetchContent = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/content');
            const data = await res.json();
            console.log("Fetched data:", data); // Debugging
            setContent(data);
        } catch (error) {
            console.error("Error fetching content:", error);
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = (text) => {
        navigator.clipboard.writeText(text);
        alert('Copied!');
    };

    return (
        <div className="min-h-screen bg-gray-50 p-8 font-sans">
            <header className="flex justify-between items-center mb-8 bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <div>
                    <h1 className="text-2xl font-bold text-gray-900">Content Dashboard</h1>
                    <p className="text-gray-500 text-sm mt-1">Manage and review your agency content</p>
                </div>
                <div className="flex gap-3">
                    <button
                        onClick={fetchContent}
                        className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 text-gray-700 transition-colors shadow-sm"
                    >
                        <RefreshCw size={18} />
                        Refresh
                    </button>
                    <button
                        onClick={() => window.location.reload()}
                        className="flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    >
                        <LogOut size={18} />
                        Logout
                    </button>
                </div>
            </header>

            {loading ? (
                <div className="flex justify-center items-center h-64">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
                </div>
            ) : content.length === 0 ? (
                <div className="text-center py-12 text-gray-500 bg-white rounded-xl shadow-sm">
                    <p>No content found. Check if the bot has generated any data.</p>
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {content.map((item, index) => (
                        <motion.div
                            key={item.id || index}
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="bg-white rounded-xl shadow-sm hover:shadow-md transition-shadow overflow-hidden border border-gray-100 flex flex-col"
                        >
                            <div className="p-5 border-b border-gray-50 bg-gray-50/30">
                                <div className="flex justify-between items-start mb-2">
                                    <span className="px-3 py-1 bg-indigo-50 text-indigo-600 text-xs font-bold uppercase tracking-wide rounded-full">
                                        {item.Brand || 'Unknown Brand'}
                                    </span>
                                    <span className="text-xs text-gray-400 font-mono">
                                        {item.Timestamp?.split(' ')[0] || 'No Date'}
                                    </span>
                                </div>
                                <h3 className="font-bold text-gray-900 line-clamp-2 text-lg leading-tight mt-2">
                                    {item.Trend || 'No Trend'}
                                </h3>
                            </div>

                            <div className="p-5 space-y-4 flex-1 flex flex-col">
                                <div className="flex-1">
                                    <p className="text-xs font-bold text-gray-400 uppercase mb-2 tracking-wider">Twitter Content</p>
                                    <p className="text-sm text-gray-600 line-clamp-4 leading-relaxed">
                                        {item.Tweet || 'No tweet content generated.'}
                                    </p>
                                </div>

                                <div className="flex gap-2 pt-4 mt-auto border-t border-gray-50">
                                    <button
                                        onClick={() => navigate(`/edit/${item.id}`, { state: { item } })}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-all text-sm font-semibold shadow-sm hover:shadow"
                                    >
                                        <Edit2 size={16} />
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => navigate(`/view/${item.id}`, { state: { item } })}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-300 transition-all text-sm font-medium"
                                    >
                                        <Eye size={16} />
                                        View
                                    </button>
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </div>
            )}
        </div>
    );
}
