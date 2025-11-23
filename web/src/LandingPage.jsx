import { useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
    Sparkles,
    TrendingUp,
    Zap,
    CheckCircle,
    ArrowRight,
    Twitter,
    Facebook,
    Instagram,
    Video,
    Users,
    BarChart3,
    Clock,
    Shield
} from 'lucide-react';

export default function LandingPage() {
    const navigate = useNavigate();
    const [email, setEmail] = useState('');

    const handleGetStarted = () => {
        navigate('/signup');
    };

    return (
        <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
            {/* Navigation */}
            <nav className="bg-white/80 backdrop-blur-md border-b border-gray-200 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex justify-between items-center h-16">
                        <div className="flex items-center gap-2">
                            <Sparkles className="text-indigo-600" size={28} />
                            <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                                Dexter
                            </span>
                        </div>
                        <div className="hidden md:flex items-center gap-8">
                            <a href="#features" className="text-gray-600 hover:text-gray-900 transition-colors">Features</a>
                            <a href="#pricing" className="text-gray-600 hover:text-gray-900 transition-colors">Pricing</a>
                            <a href="#how-it-works" className="text-gray-600 hover:text-gray-900 transition-colors">How It Works</a>
                            <button
                                onClick={() => navigate('/login')}
                                className="text-gray-600 hover:text-gray-900 transition-colors"
                            >
                                Sign In
                            </button>
                            <button
                                onClick={handleGetStarted}
                                className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition-colors font-medium"
                            >
                                Get Started
                            </button>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Hero Section */}
            <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-32">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.6 }}
                    className="text-center"
                >
                    <div className="inline-flex items-center gap-2 bg-indigo-100 text-indigo-700 px-4 py-2 rounded-full text-sm font-medium mb-8">
                        <Zap size={16} />
                        AI-Powered Content Marketing
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold text-gray-900 mb-6 leading-tight">
                        Never Miss a Trend.<br />
                        <span className="bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            Never Run Out of Content.
                        </span>
                    </h1>

                    <p className="text-xl text-gray-600 mb-12 max-w-3xl mx-auto leading-relaxed">
                        Dexter automatically detects trending topics and generates engaging social media content
                        for Twitter, Facebook, Instagram, and TikTok—all in your brand's unique voice.
                    </p>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
                        <button
                            onClick={handleGetStarted}
                            className="flex items-center gap-2 bg-indigo-600 text-white px-8 py-4 rounded-xl hover:bg-indigo-700 transition-all text-lg font-semibold shadow-lg shadow-indigo-200 hover:shadow-xl"
                        >
                            Start Free Trial <ArrowRight size={20} />
                        </button>
                        <button className="flex items-center gap-2 bg-white text-gray-700 px-8 py-4 rounded-xl hover:bg-gray-50 transition-all text-lg font-medium border border-gray-200">
                            Watch Demo <Video size={20} />
                        </button>
                    </div>

                    <div className="flex items-center justify-center gap-8 text-sm text-gray-500">
                        <div className="flex items-center gap-2">
                            <CheckCircle size={16} className="text-green-500" />
                            No credit card required
                        </div>
                        <div className="flex items-center gap-2">
                            <CheckCircle size={16} className="text-green-500" />
                            14-day free trial
                        </div>
                        <div className="flex items-center gap-2">
                            <CheckCircle size={16} className="text-green-500" />
                            Cancel anytime
                        </div>
                    </div>
                </motion.div>

                {/* Hero Image/Demo */}
                <motion.div
                    initial={{ opacity: 0, y: 40 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, delay: 0.2 }}
                    className="mt-20 relative"
                >
                    <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
                        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 p-3 flex items-center gap-2">
                            <div className="flex gap-1.5">
                                <div className="w-3 h-3 rounded-full bg-red-400"></div>
                                <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
                                <div className="w-3 h-3 rounded-full bg-green-400"></div>
                            </div>
                            <span className="text-white text-sm ml-4">Dexter Dashboard</span>
                        </div>
                        <div className="p-8 bg-gray-50">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {[1, 2, 3].map((i) => (
                                    <div key={i} className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
                                        <div className="flex items-center gap-2 mb-4">
                                            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center">
                                                <TrendingUp size={16} className="text-indigo-600" />
                                            </div>
                                            <span className="text-xs font-semibold text-indigo-600">TRENDING NOW</span>
                                        </div>
                                        <h3 className="font-bold text-gray-900 mb-2">AI Innovation {i}</h3>
                                        <p className="text-sm text-gray-600 mb-4">Generated content preview...</p>
                                        <div className="flex gap-2">
                                            <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center">
                                                <Twitter size={14} className="text-blue-600" />
                                            </div>
                                            <div className="w-6 h-6 rounded bg-blue-100 flex items-center justify-center">
                                                <Facebook size={14} className="text-blue-600" />
                                            </div>
                                            <div className="w-6 h-6 rounded bg-pink-100 flex items-center justify-center">
                                                <Instagram size={14} className="text-pink-600" />
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </motion.div>
            </section>

            {/* Features Section */}
            <section id="features" className="bg-white py-24">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">
                            Everything You Need to Dominate Social Media
                        </h2>
                        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                            Powerful features designed to save you time and boost engagement
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                        {[
                            {
                                icon: <TrendingUp className="text-indigo-600" size={28} />,
                                title: "AI Trend Detection",
                                description: "Automatically identifies trending topics relevant to your industry and location"
                            },
                            {
                                icon: <Zap className="text-purple-600" size={28} />,
                                title: "Multi-Platform Content",
                                description: "Generate content for Twitter, Facebook, Instagram Reels, and TikTok from one trend"
                            },
                            {
                                icon: <Users className="text-blue-600" size={28} />,
                                title: "Brand Voice Customization",
                                description: "Define your unique voice, tone, and style for authentic content"
                            },
                            {
                                icon: <Clock className="text-green-600" size={28} />,
                                title: "Automated Scheduling",
                                description: "Set it and forget it—content generated daily, weekly, or hourly"
                            },
                            {
                                icon: <BarChart3 className="text-orange-600" size={28} />,
                                title: "Performance Analytics",
                                description: "Track engagement, reach, and ROI across all platforms"
                            },
                            {
                                icon: <Shield className="text-red-600" size={28} />,
                                title: "Human-in-the-Loop",
                                description: "Review, edit, and approve content before publishing"
                            }
                        ].map((feature, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: index * 0.1 }}
                                viewport={{ once: true }}
                                className="bg-gray-50 p-8 rounded-2xl border border-gray-200 hover:shadow-lg transition-shadow"
                            >
                                <div className="bg-white w-14 h-14 rounded-xl flex items-center justify-center mb-4 shadow-sm">
                                    {feature.icon}
                                </div>
                                <h3 className="text-xl font-bold text-gray-900 mb-2">{feature.title}</h3>
                                <p className="text-gray-600 leading-relaxed">{feature.description}</p>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* How It Works */}
            <section id="how-it-works" className="py-24 bg-gradient-to-br from-indigo-50 to-purple-50">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">
                            How Dexter Works
                        </h2>
                        <p className="text-xl text-gray-600">
                            From trend to post in 3 simple steps
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                        {[
                            {
                                step: "01",
                                title: "Define Your Brand",
                                description: "Tell us about your business, voice, and target audience"
                            },
                            {
                                step: "02",
                                title: "AI Detects Trends",
                                description: "Our AI scans trending topics relevant to your industry"
                            },
                            {
                                step: "03",
                                title: "Review & Publish",
                                description: "Approve AI-generated content and publish to your platforms"
                            }
                        ].map((step, index) => (
                            <div key={index} className="relative">
                                <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm">
                                    <div className="text-6xl font-bold text-indigo-100 mb-4">{step.step}</div>
                                    <h3 className="text-2xl font-bold text-gray-900 mb-3">{step.title}</h3>
                                    <p className="text-gray-600 leading-relaxed">{step.description}</p>
                                </div>
                                {index < 2 && (
                                    <div className="hidden md:block absolute top-1/2 -right-4 transform -translate-y-1/2">
                                        <ArrowRight className="text-indigo-300" size={32} />
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Pricing Section */}
            <section id="pricing" className="py-24 bg-white">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="text-center mb-16">
                        <h2 className="text-4xl font-bold text-gray-900 mb-4">
                            Simple, Transparent Pricing
                        </h2>
                        <p className="text-xl text-gray-600">
                            Choose the plan that fits your needs
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                        {[
                            {
                                name: "Free",
                                price: "$0",
                                period: "forever",
                                features: ["1 brand profile", "10 content pieces/month", "Manual trend selection", "7-day history"],
                                cta: "Get Started",
                                popular: false
                            },
                            {
                                name: "Starter",
                                price: "$29",
                                period: "per month",
                                features: ["3 brand profiles", "100 content pieces/month", "Daily AI trends", "30-day history", "No watermark"],
                                cta: "Start Free Trial",
                                popular: false
                            },
                            {
                                name: "Professional",
                                price: "$99",
                                period: "per month",
                                features: ["10 brand profiles", "500 content pieces/month", "3x daily trends", "Team collaboration (3)", "API access", "Analytics"],
                                cta: "Start Free Trial",
                                popular: true
                            },
                            {
                                name: "Agency",
                                price: "$299",
                                period: "per month",
                                features: ["Unlimited brands", "2,000 content pieces/month", "Hourly trends", "Unlimited team", "White-label", "Priority support"],
                                cta: "Contact Sales",
                                popular: false
                            }
                        ].map((plan, index) => (
                            <motion.div
                                key={index}
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: index * 0.1 }}
                                viewport={{ once: true }}
                                className={`relative bg-white rounded-2xl border-2 p-8 ${plan.popular ? 'border-indigo-600 shadow-xl scale-105' : 'border-gray-200'
                                    }`}
                            >
                                {plan.popular && (
                                    <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                                        <span className="bg-indigo-600 text-white px-4 py-1 rounded-full text-sm font-semibold">
                                            Most Popular
                                        </span>
                                    </div>
                                )}
                                <h3 className="text-2xl font-bold text-gray-900 mb-2">{plan.name}</h3>
                                <div className="mb-6">
                                    <span className="text-5xl font-bold text-gray-900">{plan.price}</span>
                                    <span className="text-gray-600 ml-2">/{plan.period}</span>
                                </div>
                                <ul className="space-y-3 mb-8">
                                    {plan.features.map((feature, i) => (
                                        <li key={i} className="flex items-start gap-2 text-gray-600">
                                            <CheckCircle size={20} className="text-green-500 flex-shrink-0 mt-0.5" />
                                            <span>{feature}</span>
                                        </li>
                                    ))}
                                </ul>
                                <button
                                    onClick={handleGetStarted}
                                    className={`w-full py-3 rounded-lg font-semibold transition-colors ${plan.popular
                                            ? 'bg-indigo-600 text-white hover:bg-indigo-700'
                                            : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                                        }`}
                                >
                                    {plan.cta}
                                </button>
                            </motion.div>
                        ))}
                    </div>
                </div>
            </section>

            {/* CTA Section */}
            <section className="py-24 bg-gradient-to-r from-indigo-600 to-purple-600">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
                    <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
                        Ready to Transform Your Social Media?
                    </h2>
                    <p className="text-xl text-indigo-100 mb-12">
                        Join hundreds of businesses already using Dexter to stay ahead of trends
                    </p>
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            className="px-6 py-4 rounded-lg text-gray-900 w-full sm:w-96 focus:outline-none focus:ring-2 focus:ring-white"
                        />
                        <button
                            onClick={handleGetStarted}
                            className="bg-white text-indigo-600 px-8 py-4 rounded-lg hover:bg-gray-100 transition-colors font-semibold whitespace-nowrap"
                        >
                            Start Free Trial
                        </button>
                    </div>
                    <p className="text-indigo-200 text-sm mt-4">
                        14-day free trial • No credit card required • Cancel anytime
                    </p>
                </div>
            </section>

            {/* Footer */}
            <footer className="bg-gray-900 text-gray-400 py-12">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
                        <div>
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="text-indigo-400" size={24} />
                                <span className="text-xl font-bold text-white">Dexter</span>
                            </div>
                            <p className="text-sm">
                                AI-powered content marketing for modern businesses
                            </p>
                        </div>
                        <div>
                            <h4 className="text-white font-semibold mb-4">Product</h4>
                            <ul className="space-y-2 text-sm">
                                <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
                                <li><a href="#pricing" className="hover:text-white transition-colors">Pricing</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">API</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Integrations</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-white font-semibold mb-4">Company</h4>
                            <ul className="space-y-2 text-sm">
                                <li><a href="#" className="hover:text-white transition-colors">About</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Blog</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Contact</a></li>
                            </ul>
                        </div>
                        <div>
                            <h4 className="text-white font-semibold mb-4">Legal</h4>
                            <ul className="space-y-2 text-sm">
                                <li><a href="#" className="hover:text-white transition-colors">Privacy</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Terms</a></li>
                                <li><a href="#" className="hover:text-white transition-colors">Security</a></li>
                            </ul>
                        </div>
                    </div>
                    <div className="border-t border-gray-800 pt-8 text-center text-sm">
                        <p>&copy; 2025 Dexter. All rights reserved.</p>
                    </div>
                </div>
            </footer>
        </div>
    );
}
