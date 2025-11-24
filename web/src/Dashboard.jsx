import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Plus, LayoutGrid, Settings, LogOut, Briefcase, Shield, TrendingUp } from 'lucide-react';
import AdminUsers from './AdminUsers';
import TrendsDashboard from './TrendsDashboard';

export default function Dashboard() {
    const [user, setUser] = useState(null);
    const [brands, setBrands] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('trends'); // Default to trends now
    const navigate = useNavigate();

    useEffect(() => {
        fetchUserData();
    }, []);

    const fetchUserData = async () => {
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                navigate('/login');
                return;
            }

            // Fetch User Info
            const userRes = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });

            if (!userRes.ok) throw new Error('Failed to fetch user');
            const userData = await userRes.json();
            setUser(userData);

            // Fetch Brands
            const brandsRes = await fetch('/api/brands', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const brandsData = await brandsRes.json();
            setBrands(brandsData);

        } catch (error) {
            console.error("Error:", error);
            localStorage.removeItem('token');
            navigate('/login');
        } finally {
            setLoading(false);
        }
    };

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-50 font-sans">
            {/* Sidebar */}
            <aside className="fixed inset-y-0 left-0 w-64 bg-white border-r border-gray-200 z-10 hidden md:flex flex-col">
                <div className="p-6 border-b border-gray-100">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center text-white font-bold">
                            D
                        </div>
                        <span className="text-xl font-bold text-gray-900">Dexter</span>
                    </div>
                </div>

                <nav className="p-4 space-y-1 flex-1">
                    <button
                        onClick={() => setActiveTab('trends')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'trends'
                                ? 'bg-indigo-50 text-indigo-600'
                                : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <TrendingUp size={20} />
                        Trends
                    </button>

                    <button
                        onClick={() => setActiveTab('brands')}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'brands'
                            ? 'bg-indigo-50 text-indigo-600'
                            : 'text-gray-600 hover:bg-gray-50'
                            }`}
                    >
                        <LayoutGrid size={20} />
                        My Brands
                    </button>

                    {user?.role === 'admin' && (
                        <button
                            onClick={() => setActiveTab('admin')}
                            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${activeTab === 'admin'
                                    ? 'bg-purple-50 text-purple-600'
                                    : 'text-gray-600 hover:bg-gray-50'
                                }`}
                        >
                            <Shield size={20} />
                            Admin Panel
                        </button>
                    )}
                </nav>

                <div className="p-4 border-t border-gray-100">
                    <div className="flex items-center gap-3 px-4 py-3 mb-2">
                        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center text-gray-600 font-bold text-xs">
                            {user?.name?.[0]}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-gray-900 truncate">{user?.name}</p>
                            <p className="text-xs text-gray-500 truncate">{user?.email}</p>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors text-sm font-medium"
                    >
                        <LogOut size={16} />
                        Sign Out
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="md:ml-64 p-8">
                {activeTab === 'trends' && (
                    <div className="max-w-6xl mx-auto">
                        <TrendsDashboard brands={brands} />
                    </div>
                )}

                {activeTab === 'brands' && (
                    <div className="max-w-6xl mx-auto">
                        <header className="flex justify-between items-center mb-8">
                            <div>
                                <h1 className="text-2xl font-bold text-gray-900">My Brands</h1>
                                <p className="text-gray-500 mt-1">Manage your brands and content generation</p>
                            </div>
                            <button
                                onClick={() => navigate('/brands/new')}
                                className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm font-medium"
                            >
                                <Plus size={18} />
                                New Brand
                            </button>
                        </header>

                        {brands.length === 0 ? (
                            <div className="text-center py-16 bg-white rounded-2xl border border-dashed border-gray-300">
                                <div className="w-16 h-16 bg-indigo-50 rounded-full flex items-center justify-center mx-auto mb-4 text-indigo-600">
                                    <Briefcase size={32} />
                                </div>
                                <h3 className="text-lg font-bold text-gray-900 mb-2">No brands yet</h3>
                                <p className="text-gray-500 mb-6 max-w-sm mx-auto">
                                    Create your first brand to start generating AI-powered content for your social media.
                                </p>
                                <button
                                    onClick={() => navigate('/brands/new')}
                                    className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 transition-colors font-medium shadow-lg shadow-indigo-200"
                                >
                                    Create Your First Brand
                                </button>
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                                {brands.map((brand, index) => (
                                    <motion.div
                                        key={brand.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: index * 0.05 }}
                                        className="bg-white rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-100 overflow-hidden group cursor-pointer"
                                        onClick={() => navigate(`/brand/${brand.id}`)}
                                    >
                                        <div className="p-6">
                                            <div className="flex justify-between items-start mb-4">
                                                <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-md">
                                                    {brand.name[0]}
                                                </div>
                                                <span className={`px-2.5 py-1 rounded-full text-xs font-medium ${brand.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                                                    }`}>
                                                    {brand.is_active ? 'Active' : 'Inactive'}
                                                </span>
                                            </div>
                                            <h3 className="text-lg font-bold text-gray-900 mb-1 group-hover:text-indigo-600 transition-colors">
                                                {brand.name}
                                            </h3>
                                            <p className="text-sm text-gray-500 line-clamp-2 mb-4">
                                                {brand.description}
                                            </p>
                                            <div className="flex flex-wrap gap-2">
                                                {brand.hashtags?.slice(0, 3).map(tag => (
                                                    <span key={tag} className="text-xs bg-gray-50 text-gray-600 px-2 py-1 rounded-md border border-gray-100">
                                                        {tag}
                                                    </span>
                                                ))}
                                                {brand.hashtags?.length > 3 && (
                                                    <span className="text-xs text-gray-400 px-1 py-1">+{brand.hashtags.length - 3}</span>
                                                )}
                                            </div>
                                        </div>
                                        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between items-center">
                                            <span className="text-xs text-gray-500 font-medium">
                                                {brand.industry || 'General'}
                                            </span>
                                            <span className="text-xs font-semibold text-indigo-600 group-hover:translate-x-1 transition-transform">
                                                View Dashboard →
                                            </span>
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'admin' && user?.role === 'admin' && (
                    <AdminUsers />
                )}
            </main>
        </div>
    );
}
