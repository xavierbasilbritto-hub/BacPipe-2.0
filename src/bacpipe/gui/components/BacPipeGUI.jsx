// BacPipe 2.0 - Modern Cross-Platform GUI
// Scientific precision meets modern elegance
// BSB (Basil Britto Xavier) - UMCG/DRAIGON Project

import React, { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// Elegant Scientific Interface for BacPipe 2.0
const BacPipeGUI = () => {
  const [activeTab, setActiveTab] = useState('samples');
  const [samples, setSamples] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState('idle');
  const [realTimeProgress, setRealTimeProgress] = useState({});
  
  // Sample configuration state
  const [sampleConfig, setSampleConfig] = useState({
    sampleId: '',
    platform: 'illumina',
    readFiles: [],
    assemblyMethod: 'spades',
    modules: [],
    outputDir: ''
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-cyan-50 font-['Inter_Tight',sans-serif]">
      {/* Header with Sophisticated Branding */}
      <motion.header 
        className="bg-white/80 backdrop-blur-sm border-b border-slate-200/60 shadow-sm"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            {/* Molecular Logo */}
            <motion.div 
              className="relative"
              whileHover={{ scale: 1.05 }}
              transition={{ type: "spring", stiffness: 300 }}
            >
              <div className="w-12 h-12 relative">
                <svg viewBox="0 0 48 48" className="w-full h-full">
                  <defs>
                    <linearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style={{ stopColor: '#0891b2', stopOpacity: 1 }} />
                      <stop offset="100%" style={{ stopColor: '#155e75', stopOpacity: 1 }} />
                    </linearGradient>
                  </defs>
                  {/* DNA-like double helix simplified */}
                  <circle cx="12" cy="12" r="3" fill="url(#logoGradient)" />
                  <circle cx="36" cy="12" r="3" fill="url(#logoGradient)" />
                  <circle cx="24" cy="24" r="4" fill="url(#logoGradient)" />
                  <circle cx="12" cy="36" r="3" fill="url(#logoGradient)" />
                  <circle cx="36" cy="36" r="3" fill="url(#logoGradient)" />
                  <path 
                    d="M12 12 Q24 18 36 12 Q24 30 12 36 Q24 30 36 36" 
                    stroke="url(#logoGradient)" 
                    strokeWidth="2" 
                    fill="none"
                    opacity="0.6"
                  />
                </svg>
              </div>
            </motion.div>
            
            <div>
              <h1 className="text-2xl font-['Crimson_Pro',serif] font-semibold text-slate-800">
                BacPipe <span className="text-lg text-cyan-600 font-normal">2.0</span>
              </h1>
              <p className="text-sm text-slate-600 font-medium">
                Advanced Bacterial Genomics • AMR Detection • BSB/DRAIGON
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <PipelineStatusIndicator status={pipelineStatus} />
            <motion.button 
              className="px-4 py-2 bg-cyan-600 text-white rounded-lg font-medium hover:bg-cyan-700 transition-colors"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Settings
            </motion.button>
          </div>
        </div>
      </motion.header>

      {/* Main Interface */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Navigation Tabs */}
        <motion.nav 
          className="mb-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex space-x-1 bg-slate-100 p-1 rounded-xl">
            {[
              { id: 'samples', label: 'Sample Management', icon: '🧬' },
              { id: 'pipeline', label: 'Pipeline Config', icon: '⚙️' },
              { id: 'progress', label: 'Progress Monitor', icon: '📊' },
              { id: 'results', label: 'Results & Analysis', icon: '📈' }
            ].map((tab) => (
              <motion.button
                key={tab.id}
                className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-medium transition-all ${
                  activeTab === tab.id
                    ? 'bg-white text-cyan-700 shadow-sm'
                    : 'text-slate-600 hover:text-slate-800'
                }`}
                onClick={() => setActiveTab(tab.id)}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </motion.button>
            ))}
          </div>
        </motion.nav>

        {/* Tab Content */}
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.4 }}
          >
            {activeTab === 'samples' && <SampleManagementTab 
              samples={samples} 
              setSamples={setSamples}
              sampleConfig={sampleConfig}
              setSampleConfig={setSampleConfig}
            />}
            {activeTab === 'pipeline' && <PipelineConfigTab />}
            {activeTab === 'progress' && <ProgressMonitorTab progress={realTimeProgress} />}
            {activeTab === 'results' && <ResultsAnalysisTab />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

// Pipeline Status Indicator Component
const PipelineStatusIndicator = ({ status }) => {
  const statusConfig = {
    idle: { color: 'text-slate-500', bg: 'bg-slate-100', label: 'Idle' },
    running: { color: 'text-cyan-600', bg: 'bg-cyan-100', label: 'Running' },
    completed: { color: 'text-emerald-600', bg: 'bg-emerald-100', label: 'Completed' },
    error: { color: 'text-red-600', bg: 'bg-red-100', label: 'Error' }
  };
  
  const config = statusConfig[status] || statusConfig.idle;
  
  return (
    <div className={`flex items-center space-x-2 px-3 py-2 rounded-full ${config.bg}`}>
      <motion.div 
        className={`w-2 h-2 rounded-full ${config.color.replace('text-', 'bg-')}`}
        animate={status === 'running' ? { scale: [1, 1.2, 1] } : {}}
        transition={{ repeat: status === 'running' ? Infinity : 0, duration: 1 }}
      />
      <span className={`text-sm font-medium ${config.color}`}>
        {config.label}
      </span>
    </div>
  );
};

// Sample Management Tab
const SampleManagementTab = ({ samples, setSamples, sampleConfig, setSampleConfig }) => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      {/* Add New Sample Form */}
      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Add New Sample
        </h3>
        
        <div className="space-y-4">
          {/* Sample ID */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Sample ID
            </label>
            <input
              type="text"
              className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              placeholder="e.g., BSB_MRSA_001"
              value={sampleConfig.sampleId}
              onChange={(e) => setSampleConfig(prev => ({ ...prev, sampleId: e.target.value }))}
            />
          </div>

          {/* Sequencing Platform */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Sequencing Platform
            </label>
            <select 
              className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              value={sampleConfig.platform}
              onChange={(e) => setSampleConfig(prev => ({ ...prev, platform: e.target.value }))}
            >
              <option value="illumina">📱 Illumina (Short Reads)</option>
              <option value="ont">🧬 Oxford Nanopore (Long Reads)</option>
              <option value="hybrid">🔄 Hybrid (Illumina + ONT)</option>
              <option value="pacbio">📡 PacBio (Long Reads)</option>
            </select>
          </div>

          {/* Assembly Method */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">
              Assembly Method
            </label>
            <select 
              className="w-full px-4 py-3 border border-slate-200 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              value={sampleConfig.assemblyMethod}
              onChange={(e) => setSampleConfig(prev => ({ ...prev, assemblyMethod: e.target.value }))}
            >
              {sampleConfig.platform === 'illumina' && (
                <>
                  <option value="spades">SPAdes (Recommended)</option>
                  <option value="skesa">SKESA (Fast)</option>
                  <option value="velvet">Velvet (Legacy)</option>
                </>
              )}
              {sampleConfig.platform === 'ont' && (
                <>
                  <option value="flye">Flye (Recommended)</option>
                  <option value="canu">Canu (High Quality)</option>
                  <option value="raven">Raven (Fast)</option>
                  <option value="miniasm">Miniasm (Ultra Fast)</option>
                </>
              )}
              {sampleConfig.platform === 'hybrid' && (
                <>
                  <option value="unicycler">Unicycler (Recommended)</option>
                  <option value="hybrid_spades">Hybrid SPAdes</option>
                </>
              )}
            </select>
          </div>

          {/* Analysis Modules */}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Analysis Modules
            </label>
            <div className="grid grid-cols-2 gap-2">
              {[
                { id: 'qc', label: 'Quality Control', icon: '✅' },
                { id: 'assembly', label: 'Assembly', icon: '🧩' },
                { id: 'annotation', label: 'Annotation', icon: '📝' },
                { id: 'mlst', label: 'MLST Typing', icon: '🔍' },
                { id: 'amr', label: 'AMR Detection', icon: '🛡️' },
                { id: 'mcr_screening', label: 'mcr Screening', icon: '🎯' },
                { id: 'vanp_detection', label: 'vanP Detection', icon: '🔬' },
                { id: 'virulence', label: 'Virulence', icon: '⚠️' }
              ].map((module) => (
                <motion.label
                  key={module.id}
                  className="flex items-center space-x-2 p-3 border border-slate-200 rounded-lg cursor-pointer hover:bg-slate-50 transition-colors"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <input
                    type="checkbox"
                    className="text-cyan-600 focus:ring-cyan-500"
                    checked={sampleConfig.modules.includes(module.id)}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSampleConfig(prev => ({ 
                          ...prev, 
                          modules: [...prev.modules, module.id] 
                        }));
                      } else {
                        setSampleConfig(prev => ({ 
                          ...prev, 
                          modules: prev.modules.filter(m => m !== module.id) 
                        }));
                      }
                    }}
                  />
                  <span className="text-sm">{module.icon}</span>
                  <span className="text-sm font-medium">{module.label}</span>
                </motion.label>
              ))}
            </div>
          </div>

          {/* Add Sample Button */}
          <motion.button 
            className="w-full py-3 bg-gradient-to-r from-cyan-600 to-cyan-700 text-white rounded-lg font-medium hover:from-cyan-700 hover:to-cyan-800 transition-all"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={() => {
              if (sampleConfig.sampleId) {
                setSamples(prev => [...prev, { ...sampleConfig, id: Date.now() }]);
                setSampleConfig({ sampleId: '', platform: 'illumina', readFiles: [], assemblyMethod: 'spades', modules: [], outputDir: '' });
              }
            }}
          >
            Add Sample to Queue
          </motion.button>
        </div>
      </motion.div>

      {/* Sample Queue */}
      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Sample Queue ({samples.length})
        </h3>
        
        <div className="space-y-3">
          {samples.length === 0 ? (
            <div className="text-center py-8 text-slate-500">
              <div className="text-4xl mb-2">🧬</div>
              <p>No samples in queue</p>
              <p className="text-sm">Add samples to get started</p>
            </div>
          ) : (
            samples.map((sample, index) => (
              <motion.div
                key={sample.id}
                className="flex items-center justify-between p-4 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <div>
                  <h4 className="font-medium text-slate-800">{sample.sampleId}</h4>
                  <p className="text-sm text-slate-600">
                    {sample.platform} • {sample.assemblyMethod} • {sample.modules.length} modules
                  </p>
                </div>
                <motion.button
                  className="text-red-500 hover:text-red-700 transition-colors"
                  whileHover={{ scale: 1.1 }}
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setSamples(prev => prev.filter(s => s.id !== sample.id))}
                >
                  🗑️
                </motion.button>
              </motion.div>
            ))
          )}
        </div>

        {samples.length > 0 && (
          <motion.button 
            className="w-full mt-6 py-3 bg-gradient-to-r from-emerald-600 to-emerald-700 text-white rounded-lg font-medium hover:from-emerald-700 hover:to-emerald-800 transition-all"
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            🚀 Start Pipeline ({samples.length} samples)
          </motion.button>
        )}
      </motion.div>
    </div>
  );
};

// Pipeline Configuration Tab
const PipelineConfigTab = () => {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Resource Settings
        </h3>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">CPU Threads</label>
            <input type="number" className="w-full px-4 py-3 border border-slate-200 rounded-lg" defaultValue="8" />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Memory Limit</label>
            <select className="w-full px-4 py-3 border border-slate-200 rounded-lg">
              <option>16GB</option>
              <option>32GB</option>
              <option>64GB</option>
            </select>
          </div>
        </div>
      </motion.div>

      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Database Status
        </h3>
        
        <div className="space-y-3">
          {[
            { name: 'CARD Database', version: 'v3.3.0', status: 'updated' },
            { name: 'ResFinder', version: 'v4.5.0', status: 'updated' },
            { name: 'mcr Database', version: 'Custom', status: 'updated' },
            { name: 'VirulenceFinder', version: 'v2.0.8', status: 'update_available' }
          ].map((db, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-slate-50 rounded-lg">
              <div>
                <span className="font-medium">{db.name}</span>
                <span className="text-sm text-slate-600 ml-2">{db.version}</span>
              </div>
              <span className={`px-2 py-1 text-xs rounded ${
                db.status === 'updated' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
              }`}>
                {db.status === 'updated' ? '✅ Updated' : '⚠️ Update Available'}
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

// Progress Monitor Tab
const ProgressMonitorTab = ({ progress }) => {
  return (
    <div className="space-y-6">
      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Real-time Progress Monitor
        </h3>
        
        <div className="text-center py-12 text-slate-500">
          <motion.div 
            className="text-6xl mb-4"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          >
            🧬
          </motion.div>
          <p className="text-lg">No active pipeline runs</p>
          <p className="text-sm">Progress will appear here when processing samples</p>
        </div>
      </motion.div>
    </div>
  );
};

// Results & Analysis Tab
const ResultsAnalysisTab = () => {
  return (
    <div className="space-y-6">
      <motion.div 
        className="bg-white rounded-xl shadow-sm border border-slate-200 p-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <h3 className="text-lg font-['Crimson_Pro',serif] font-semibold text-slate-800 mb-6">
          Analysis Results & Reports
        </h3>
        
        <div className="text-center py-12 text-slate-500">
          <div className="text-6xl mb-4">📊</div>
          <p className="text-lg">No results available</p>
          <p className="text-sm">Complete sample processing to view results</p>
        </div>
      </motion.div>
    </div>
  );
};

export default BacPipeGUI;
