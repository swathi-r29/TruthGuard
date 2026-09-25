import React, { useState, useEffect } from 'react';

const API_BASE = 'http://localhost:8000';

export default function App() {
  const [activeTab, setActiveTab] = useState('analyze');
  const [loading, setLoading] = useState(false);
  const [pipelineStep, setPipelineStep] = useState(1);
  const [analysisError, setAnalysisError] = useState('');
  const [showAmortTable, setShowAmortTable] = useState(false);
  const [strategySubTab, setStrategySubTab] = useState('roadmap');
  const [compLoans, setCompLoans] = useState([
    { name: 'Offer A', principal: 200000, interestRate: 15.0, tenure: 24, emi: 9697, pf: 2.0, ins: 3000 },
    { name: 'Offer B', principal: 200000, interestRate: 14.5, tenure: 24, emi: 9650, pf: 1.5, ins: 0 },
    { name: 'Offer C', principal: 200000, interestRate: 16.0, tenure: 24, emi: 9792, pf: 0.0, ins: 5000 }
  ]);
  
  // Backend health status
  const [apiHealth, setApiHealth] = useState({ online: false, provider: '', model: '' });
  
  // AI Chatbot state
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI Loan Assistant. Ask me any questions about the clauses, terms, or penalties in your uploaded loan agreement.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  
  // Analyzed data state (holds metrics, charges, transparency, explanations, rates, etc.)
  const [analysis, setAnalysis] = useState(null);
  
  // Manual Entry Form State
  const [manualForm, setManualForm] = useState({
    principal: 200000,
    interest_rate_annual: 18.0,
    tenure_months: 24,
    interest_type: 'reducing_balance',
    emi: 9984.82,
    charges: [
      { canonical_name: 'processing_fee', original_name: 'Processing Fee', value: 2.0, unit: 'percent', basis: 'principal', classification: 'ADDITIONAL_COST', is_mandatory: true, is_conditional: false },
      { canonical_name: 'documentation_fee', original_name: 'Documentation Fee', value: 750.0, unit: 'INR', basis: 'flat', classification: 'ADDITIONAL_COST', is_mandatory: true, is_conditional: false },
      { canonical_name: 'insurance', original_name: 'Insurance Premium', value: 3500.0, unit: 'INR', basis: 'flat', classification: 'OPTIONAL_COST', is_mandatory: false, is_conditional: false },
      { canonical_name: 'gst_tax_references', original_name: 'GST', value: 18.0, unit: 'percent', basis: 'flat', classification: 'TAX', is_mandatory: true, is_conditional: false },
      { canonical_name: 'foreclosure_charge', original_name: 'Foreclosure Charge', value: 4.0, unit: 'percent', basis: 'outstanding_principal', classification: 'CONDITIONAL_COST', is_mandatory: false, is_conditional: true },
      { canonical_name: 'late_payment_fee', original_name: 'Late Payment Fee', value: 500.0, unit: 'INR', basis: 'flat', classification: 'PENALTY', is_mandatory: false, is_conditional: true },
      { canonical_name: 'bounce_charge', original_name: 'Bounce Charge', value: 450.0, unit: 'INR', basis: 'flat', classification: 'PENALTY', is_mandatory: false, is_conditional: true }
    ]
  });

  // Payoff Simulator State
  const [simParams, setSimParams] = useState({
    balance: 0,
    rate_annual: 0,
    current_emi: 0,
    extra_monthly: 1000,
    one_time_payment: 0,
    one_time_month: 1
  });
  const [simResult, setSimResult] = useState(null);

  // Multi-Debt Strategy State
  const [debts, setDebts] = useState([]);
  const [strategy, setStrategy] = useState('avalanche');
  const [strategyResult, setStrategyResult] = useState(null);

  // Dispute & Negotiation Letter State
  const [disputeBorrowerName, setDisputeBorrowerName] = useState('John Doe');
  const [disputeSelectedCharges, setDisputeSelectedCharges] = useState([]);
  const [disputeCustomNotes, setDisputeCustomNotes] = useState('');

  // Fetch backend status on mount
  useEffect(() => {
    fetchHealth();
  }, []);

  // Prepopulate simulator inputs when analysis changes
  useEffect(() => {
    if (analysis && analysis.metrics) {
      const outstanding = analysis.charges.find(c => c.canonical_name === 'outstanding_principal')?.value || analysis.metrics.loan_amount;
      const loanBal = parseFloat(outstanding) || 0;
      const loanRate = parseFloat(analysis.metrics.interest_rate_annual) || 0;
      const loanEmi = parseFloat(analysis.metrics.emi) || 0;

      setSimParams(prev => ({
        ...prev,
        balance: loanBal,
        rate_annual: loanRate,
        current_emi: loanEmi
      }));

      // Prepopulate multi-debt catalog ONLY with active loan
      const activeLoanName = analysis.doc_name || 'Active Loan';
      setDebts([
        {
          id: Date.now(),
          name: activeLoanName.length > 25 ? activeLoanName.slice(0, 25) + '...' : activeLoanName,
          balance: loanBal,
          interest_rate: loanRate,
          emi: loanEmi
        }
      ]);

      // Prepopulate Offer A in comparison matrix
      setCompLoans(prev => {
        const next = [...prev];
        const pf_val = analysis.charges.find(c => c.canonical_name === 'processing_fee_percentage')?.value || 0;
        const ins_val = analysis.charges.find(c => c.canonical_name === 'insurance')?.value || 0;
        next[0] = {
          name: 'Active Audited Loan',
          principal: parseFloat(analysis.metrics.loan_amount) || 0,
          interestRate: parseFloat(analysis.metrics.interest_rate_annual) || 0,
          tenure: parseInt(analysis.metrics.tenure_months) || 0,
          emi: parseFloat(analysis.metrics.emi) || 0,
          pf: parseFloat(pf_val) || 0,
          ins: parseFloat(ins_val) || 0
        };
        return next;
      });

      // Prepopulate selected charges for dispute letter
      if (analysis.charges) {
        setDisputeSelectedCharges(analysis.charges.map(c => c.canonical_name));
      }
    }
  }, [analysis]);

  // Run Payoff Simulation automatically when parameters change
  useEffect(() => {
    runPayoffSimulation();
  }, [simParams]);

  // Run Strategy prioritize automatically when debt list or strategy changes
  useEffect(() => {
    runStrategyComparison();
  }, [debts, strategy]);

  const fetchHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/health`);
      const data = await res.json();
      if (data.status === 'ok') {
        setApiHealth({ online: true, provider: data.llm_provider, model: data.llm_model });
      }
    } catch (err) {
      setApiHealth({ online: false, provider: '', model: '' });
    }
  };

  const handleSendChatMessage = async () => {
    if (!chatInput.trim()) return;
    
    const userMsg = { role: 'user', content: chatInput };
    setChatMessages(prev => [...prev, userMsg]);
    setChatInput('');
    setChatLoading(true);
    
    // We compile the context from active audited loan metrics/charges or raw text if available
    let contextText = "No active document analyzed. Please guide the user to upload their document.";
    if (analysis) {
      contextText = `
Document Name: ${analysis.doc_name}
Sanctioned Amount: ₹${analysis.metrics.loan_amount}
Nominal Interest Rate: ${analysis.metrics.interest_rate_annual}% p.a.
Tenure: ${analysis.metrics.tenure_months} Months
Stated EMI: ₹${analysis.metrics.emi}
True Effective APR: ${analysis.effective_rates?.effective_annual_cost_rate || analysis.metrics.interest_rate_annual}%
Transparency Score: ${analysis.transparency?.score}/100

Extracted Charges:
${analysis.charges.map(c => `- ${c.canonical_name}: ${c.value} ${c.unit} (${c.basis}) [Evidence: ${c.evidence}]`).join('\n')}

Regulatory Warnings:
${analysis.compliance_alerts ? analysis.compliance_alerts.map(a => `- ${a.title}: ${a.description} [Ref: ${a.law_reference}]`).join('\n') : 'None'}

Document Text:
${analysis.document_text || ''}
`;
    }
    
    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMsg.content,
          context_text: contextText,
          history: chatMessages.slice(1)
        })
      });
      const data = await res.json();
      setChatMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (err) {
      console.error(err);
      setChatMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, I failed to reach the AI engine. Please verify the backend is running.' }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setAnalysis(null);
    setDebts([]);
    setAnalysisError('');
    
    // Animate Pipeline Stepper
    let step = 1;
    setPipelineStep(1);
    const stepInterval = setInterval(() => {
      if (step < 5) {
        step += 1;
        setPipelineStep(step);
      }
    }, 1500);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();
      
      clearInterval(stepInterval);
      
      if (data.success) {
        setPipelineStep(6);
        setTimeout(() => {
          setAnalysis(data);
          setLoading(false);
          setActiveTab('dashboard');
        }, 800);
      } else {
        setAnalysisError(data.error || 'Failed to analyze document.');
        setLoading(false);
      }
    } catch (err) {
      clearInterval(stepInterval);
      setAnalysisError('Network error connecting to API. Please ensure FastAPI is running.');
      setLoading(false);
    }
  };

  const loadSampleDocument = async (sampleName) => {
    setLoading(true);
    setAnalysisError('');
    setPipelineStep(1);

    // Fetch the sample file bytes
    try {
      // Simulate stepper progress
      let step = 1;
      const stepInterval = setInterval(() => {
        if (step < 6) {
          step += 1;
          setPipelineStep(step);
        }
      }, 300);

      // Create a dummy file upload matching the sample
      const response = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: new FormData() // empty, but backend handles signature matches by sample files
      });

      // To work around empty upload on browser side, we fetch the actual pdf if available,
      // or we simulate using mock calculated data by mapping the sample name to a mock file
      // Apex, SplitPay, Nova, QuickMicro, DebtDetox Sample are supported by sending file name as query/form.
      // Let's create a custom blob for signature
      let signature = "";
      if (sampleName.includes("apex")) signature = "APEX LENDING SERVICES";
      else if (sampleName.includes("splitpay")) signature = "SPLITPAY FINANCE";
      else if (sampleName.includes("nova")) signature = "NOVA TRUST BANK";
      else if (sampleName.includes("scanned")) signature = "QUICKMICRO FINANCE";
      else signature = "DEBT DETOX VALIDATION";

      const blob = new Blob([signature], { type: 'application/pdf' });
      const formData = new FormData();
      formData.append('file', blob, sampleName);

      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json();

      clearInterval(stepInterval);

      if (data.success) {
        setPipelineStep(6);
        setTimeout(() => {
          setAnalysis(data);
          setLoading(false);
          setActiveTab('dashboard');
        }, 500);
      } else {
        setAnalysisError(data.error || 'Failed to process sample.');
        setLoading(false);
      }
    } catch (err) {
      clearInterval(stepInterval);
      setAnalysisError('Failed to connect to backend.');
      setLoading(false);
    }
  };

  const handleManualCalculate = async (e) => {
    e.preventDefault();
    setLoading(true);
    setAnalysisError('');

    try {
      const res = await fetch(`${API_BASE}/api/calculate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(manualForm)
      });
      const data = await res.json();
      
      if (data.success) {
        setAnalysis(data);
        setLoading(false);
        setActiveTab('dashboard');
      } else {
        setAnalysisError(data.detail || 'Manual calculation failed.');
        setLoading(false);
      }
    } catch (err) {
      setAnalysisError('Failed to communicate with calculation service.');
      setLoading(false);
    }
  };

  const runPayoffSimulation = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/simulate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(simParams)
      });
      const data = await res.json();
      if (data.success) {
        setSimResult(data);
      }
    } catch (err) {
      console.error('Simulation API failed:', err);
    }
  };

  const runStrategyComparison = async () => {
    try {
      const cleanDebts = debts.map(({ name, balance, interest_rate, emi }) => ({
        name, balance, interest_rate, emi
      }));
      const res = await fetch(`${API_BASE}/api/strategy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ debts: cleanDebts, strategy })
      });
      const data = await res.json();
      setStrategyResult(data);
    } catch (err) {
      console.error('Strategy comparison failed:', err);
    }
  };

  const addManualDebt = () => {
    setDebts(prev => [
      ...prev,
      {
        id: Date.now(),
        name: `New Debt ${prev.length + 1}`,
        balance: 50000,
        interest_rate: 18.0,
        emi: 2500
      }
    ]);
  };

  const removeDebt = (id) => {
    setDebts(prev => prev.filter(d => d.id !== id));
  };

  const updateDebtItem = (id, key, val) => {
    setDebts(prev => prev.map(d => d.id === id ? { ...d, [key]: parseFloat(val) || 0 } : d));
  };

  const generateDisputeLetterText = () => {
    if (!analysis) return '';
    const dateStr = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
    const docRef = analysis.doc_name || 'Loan Agreement';
    const principal = analysis.metrics?.loan_amount || 0;
    const statedRate = analysis.metrics?.interest_rate_annual || 0;
    const realApr = analysis.effective_rates?.effective_annual_cost_rate || statedRate;
    const tenure = analysis.metrics?.tenure_months || 0;
    const upfrontFees = analysis.metrics?.upfront_fees || 0;
    const netDisbursed = analysis.metrics?.net_disbursed_amount || principal;

    const selectedList = (analysis.charges || []).filter(c => disputeSelectedCharges.includes(c.canonical_name));

    let letter = `FORMAL REQUEST FOR FEE WAIVER & CONTRACT RE-EXAMINATION\n\nDate: ${dateStr}\nTo: The Loan Operations & Grievance Redressal Officer\nRe: Contract Audit & Dispute Notice — Reference: ${docRef}\nBorrower Name: ${disputeBorrowerName}\n\n--------------------------------------------------------------------------------\n\nDear Sir/Madam,\n\nI am writing to formally request a review and re-examination of specific terms, fee structures, and disclosure conditions contained in my credit agreement (${docRef}).\n\nAn independent financial audit of the contract terms reveals significant divergences between advertised loan costs and total effective debt obligations:\n\nSUMMARY OF AUDIT FINDINGS:\n--------------------------\n1. Sanctioned Principal Amount: ₹${principal.toLocaleString('en-IN')}\n2. Stated Annual Interest Rate: ${statedRate}% p.a.\n3. Effective Annual Rate (Real APR): ${realApr.toFixed(2)}% p.a. (Hidden APR Markup: +${(realApr - statedRate).toFixed(2)}%)\n4. Upfront Deductions & Fees: ₹${upfrontFees.toLocaleString('en-IN')} (Net Disbursement: ₹${netDisbursed.toLocaleString('en-IN')})\n5. Repayment Tenure: ${tenure} Months\n\nSPECIFIC CLAUSES UNDER DISPUTE / REQUEST FOR WAIVER:\n---------------------------------------------------\n`;

    if (selectedList.length === 0) {
      letter += `• Upfront Fee Structure: General request to review processing and administrative deductions.\n`;
    } else {
      selectedList.forEach((charge, idx) => {
        const name = charge.original_name || charge.canonical_name.replace(/_/g, ' ');
        const val = charge.value;
        const unit = charge.unit;
        let val_str = 'Not Specified';
        if (val !== null && val !== undefined) {
          if (unit === 'percent') val_str = `${val}%`;
          else if (unit === 'INR') val_str = `₹${val.toLocaleString('en-IN')}`;
          else val_str = `${val} ${unit}`;
        }
        letter += `${idx + 1}. Clause / Charge: ${name} (${val_str})\n   - Basis: ${(charge.basis || '').replace(/_/g, ' ')}\n   - Contract Evidence (Page ${charge.page || 1}): "${charge.evidence || ''}"\n`;
        if (charge.canonical_name.includes('foreclosure') || charge.canonical_name.includes('prepayment')) {
          letter += `   - Ground for Waiver: Central bank consumer guidelines prohibit foreclosure penalties on floating-rate individual retail credit.\n`;
        } else if (charge.canonical_name.includes('processing')) {
          letter += `   - Ground for Waiver: Upfront processing fee exceeds standard benchmarks and reduces net disbursement cash in hand.\n`;
        } else if (charge.canonical_name.includes('bounce') || charge.canonical_name.includes('late')) {
          letter += `   - Ground for Waiver: Penal default charges must be reasonable and strictly cost-reflective rather than punitive.\n`;
        }
        letter += `\n`;
      });
    }

    if (analysis.compliance_alerts && analysis.compliance_alerts.length > 0) {
      letter += `REGULATORY & FAIR PRACTICE CONCERNS:\n------------------------------------\n`;
      analysis.compliance_alerts.forEach(alert => {
        letter += `• [${alert.severity || 'WARNING'}] ${alert.title}: ${alert.description}\n  Reference Standard: ${alert.law_reference || ''}\n`;
      });
      letter += `\n`;
    }

    if (disputeCustomNotes.trim()) {
      letter += `ADDITIONAL BORROWER STATEMENT:\n------------------------------\n${disputeCustomNotes.trim()}\n\n`;
    }

    letter += `FORMAL RELIEF REQUESTED:\n------------------------\nIn light of the above findings, I respectfully request that your institution:\n1. Waive or reduce the disputed upfront and penalty fees listed above prior to final settlement.\n2. Provide a clear, written APR disclosure breakdown confirming the net effective interest rate.\n3. Confirm in writing that no un-disclosed post-disbursement fees will be levied.\n\nI look forward to your prompt response and written confirmation within 7 working days.\n\nSincerely,\n\n_______________________________\n${disputeBorrowerName}\nContact Reference: ${docRef}\nAudit Verification Code: DEBT-DETOX-AUDIT\n`;

    return letter;
  };

  // Transparency Score verdict helper
  const getVerdictDetails = (score) => {
    if (score >= 80) {
      return { text: 'Consumer Friendly', color: '#10b981', bg: 'rgba(16, 185, 129, 0.1)', desc: 'This contract contains fair standard terms, low penalty exposure, and comprehensive clause transparency.' };
    } else if (score >= 60) {
      return { text: 'Moderate Caution', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.1)', desc: 'The contract has multiple additional fees or prepayment locking periods. Review the terms before signing.' };
    } else {
      return { text: 'High Risk / Predatory', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.1)', desc: 'Extremely high penalties, compound late charges, or missing key parameters. Proceed with extreme caution.' };
    }
  };

  const calculateReducingEmi = (p, annualRate, n) => {
    if (p <= 0 || annualRate <= 0 || n <= 0) return 0;
    const r = (annualRate / 12.0) / 100.0;
    return (p * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
  };

  const solveMonthlyIrrJS = (netDisbursed, emi, tenure) => {
    if (netDisbursed <= 0 || emi <= 0 || tenure <= 0) return 0;
    if (emi * tenure <= netDisbursed) return 0.0;
    let low = 0.0;
    let high = 2.0;
    let tolerance = 1e-9;
    for (let i = 0; i < 100; i++) {
      let mid = (low + high) / 2.0;
      let npv = 0.0;
      for (let t = 1; t <= tenure; t++) {
        npv += emi / Math.pow(1 + mid, t);
      }
      let diff = npv - netDisbursed;
      if (Math.abs(diff) < tolerance) return mid;
      if (diff > 0) low = mid;
      else high = mid;
    }
    return low;
  };

  const calculateEffectiveAprJS = (netDisbursed, emi, tenure) => {
    const irrMonthly = solveMonthlyIrrJS(netDisbursed, emi, tenure);
    const effectiveAnnual = (Math.pow(1.0 + irrMonthly, 12.0) - 1.0) * 100.0;
    return effectiveAnnual;
  };

  const generateAmortizationSchedule = (principal, annualRate, tenureMonths, emi) => {
    const schedule = [];
    let outstanding = principal;
    const monthlyRate = (annualRate / 100.0) / 12.0;
    
    for (let m = 1; m <= tenureMonths; m++) {
      if (outstanding <= 0) break;
      const interest = outstanding * monthlyRate;
      let pPay = emi - interest;
      let actualEmi = emi;
      if (pPay > outstanding || m === tenureMonths) {
        pPay = outstanding;
        actualEmi = pPay + interest;
      }
      
      const outstandingNew = outstanding - pPay;
      schedule.push({
        month: m,
        emi: actualEmi,
        interest: interest,
        principal: pPay,
        closing_balance: Math.max(0.0, outstandingNew)
      });
      outstanding = outstandingNew;
    }
    return schedule;
  };

  const renderDashboardAmortizationTimeline = (schedule, principal) => {
    if (!schedule || schedule.length === 0) return null;
    const maxMonths = schedule.length;
    const maxBalance = principal;
    
    const width = 600;
    const height = 200;
    const paddingLeft = 50;
    const paddingRight = 20;
    const paddingTop = 20;
    const paddingBottom = 30;

    const getX = (m) => paddingLeft + (m / maxMonths) * (width - paddingLeft - paddingRight);
    const getY = (bal) => height - paddingBottom - (bal / maxBalance) * (height - paddingTop - paddingBottom);

    const points = schedule.map(d => `${getX(d.month)},${getY(d.closing_balance)}`).join(' ');
    const fillPoints = `${getX(0)},${getY(maxBalance)} ` + points + ` ${getX(maxMonths)},${getY(0)} ${getX(0)},${getY(0)}`;

    return (
      <div className="chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="timeline-svg">
          <defs>
            <linearGradient id="dashGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={paddingLeft} y1={getY(maxBalance)} x2={width - paddingRight} y2={getY(maxBalance)} stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
          <line x1={paddingLeft} y1={getY(maxBalance/2)} x2={width - paddingRight} y2={getY(maxBalance/2)} stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
          <line x1={paddingLeft} y1={height - paddingBottom} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(255,255,255,0.08)" />

          {/* Area Fill */}
          <polygon points={fillPoints} fill="url(#dashGrad)" />

          {/* Line Plot */}
          <polyline points={points} fill="none" stroke="#06b6d4" strokeWidth="3" />

          {/* Marker */}
          <circle cx={getX(maxMonths)} cy={getY(0)} r="5" fill="#06b6d4" />

          {/* Y Axis Labels */}
          <text x={paddingLeft - 8} y={getY(maxBalance) + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹{Math.round(maxBalance/1000)}k</text>
          <text x={paddingLeft - 8} y={getY(maxBalance/2) + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹{Math.round((maxBalance/2)/1000)}k</text>
          <text x={paddingLeft - 8} y={height - paddingBottom + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹0</text>

          {/* X Axis Labels */}
          <text x={getX(0)} y={height - paddingBottom + 16} fill="#94A3B8" fontSize="9" textAnchor="middle">M0</text>
          <text x={getX(maxMonths)} y={height - paddingBottom + 16} fill="#06b6d4" fontSize="9" fontWeight="bold" textAnchor="middle">M{maxMonths}</text>
        </svg>
      </div>
    );
  };

  // Rendering standard custom SVG line timeline for payoff simulation
  const renderAmortizationTimeline = () => {
    if (!simResult) return null;
    const { normal_schedule, accelerated_schedule, normal_months, accelerated_months, balance } = simResult;
    const maxMonths = Math.max(normal_months, accelerated_months);
    const maxBalance = balance;
    
    const width = 600;
    const height = 200;
    const paddingLeft = 50;
    const paddingRight = 20;
    const paddingTop = 20;
    const paddingBottom = 30;

    const getX = (m) => paddingLeft + (m / maxMonths) * (width - paddingLeft - paddingRight);
    const getY = (bal) => height - paddingBottom - (bal / maxBalance) * (height - paddingTop - paddingBottom);

    // Normal line points
    const normalPoints = normal_schedule.map(d => `${getX(d.month)},${getY(d.closing_balance)}`).join(' ');
    // Accelerated line points
    const accPoints = accelerated_schedule.map(d => `${getX(d.month)},${getY(d.closing_balance)}`).join(' ');

    // Fill points (anchoring to bottom-zero line)
    const normalFillPoints = `${getX(0)},${getY(maxBalance)} ` + normalPoints + ` ${getX(normal_months)},${getY(0)} ${getX(0)},${getY(0)}`;
    const accFillPoints = `${getX(0)},${getY(maxBalance)} ` + accPoints + ` ${getX(accelerated_months)},${getY(0)} ${getX(0)},${getY(0)}`;

    return (
      <div className="chart-container">
        <svg viewBox={`0 0 ${width} ${height}`} className="timeline-svg">
          {/* Gradients */}
          <defs>
            <linearGradient id="normGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#EF4444" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#EF4444" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="accGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.15" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={paddingLeft} y1={getY(maxBalance)} x2={width - paddingRight} y2={getY(maxBalance)} stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
          <line x1={paddingLeft} y1={getY(maxBalance/2)} x2={width - paddingRight} y2={getY(maxBalance/2)} stroke="rgba(255,255,255,0.04)" strokeDasharray="3 3" />
          <line x1={paddingLeft} y1={height - paddingBottom} x2={width - paddingRight} y2={height - paddingBottom} stroke="rgba(255,255,255,0.08)" />

          {/* Area Fills */}
          <polygon points={normalFillPoints} fill="url(#normGrad)" />
          <polygon points={accFillPoints} fill="url(#accGrad)" />

          {/* Line Plots */}
          <polyline points={normalPoints} fill="none" stroke="#EF4444" strokeWidth="3" />
          <polyline points={accPoints} fill="none" stroke="#10B981" strokeWidth="3.5" />

          {/* Markers */}
          <circle cx={getX(normal_months)} cy={getY(0)} r="5" fill="#EF4444" />
          <circle cx={getX(accelerated_months)} cy={getY(0)} r="6" fill="#10B981" />

          {/* Y Axis Labels */}
          <text x={paddingLeft - 8} y={getY(maxBalance) + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹{Math.round(maxBalance/1000)}k</text>
          <text x={paddingLeft - 8} y={getY(maxBalance/2) + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹{Math.round((maxBalance/2)/1000)}k</text>
          <text x={paddingLeft - 8} y={height - paddingBottom + 4} fill="#94A3B8" fontSize="9" textAnchor="end">₹0</text>

          {/* X Axis Labels */}
          <text x={getX(0)} y={height - paddingBottom + 16} fill="#94A3B8" fontSize="9" textAnchor="middle">M0</text>
          <text x={getX(accelerated_months)} y={height - paddingBottom + 16} fill="#10B981" fontSize="9" fontWeight="bold" textAnchor="middle">M{accelerated_months}</text>
          <text x={getX(normal_months)} y={height - paddingBottom + 16} fill="#EF4444" fontSize="9" fontWeight="bold" textAnchor="middle">M{normal_months}</text>
        </svg>
      </div>
    );
  };

  return (
    <div className="app-container">
      {/* SIDEBAR NAVIGATION */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="icon">🛡️</span>
          <div>
            <h2 className="sidebar-title">DEBT DETOX</h2>
            <div className="sidebar-subtitle">AI Debt Cost Auditor</div>
          </div>
        </div>

        {/* ACTIVE LOAN CARD */}
        {analysis ? (
          <div className="active-loan-profile">
            <div className="profile-header">
              <span>Active Loan Audit</span>
              <span 
                className="profile-status-badge" 
                style={{ 
                  color: getVerdictDetails(analysis.transparency.score).color,
                  backgroundColor: getVerdictDetails(analysis.transparency.score).bg 
                }}
              >
                {analysis.audit_status}
              </span>
            </div>
            <div className="profile-filename" title={analysis.doc_name}>📄 {analysis.doc_name}</div>
            <div className="profile-stats">
              <div className="profile-stat-row">
                <span>Principal:</span>
                <span>₹{analysis.metrics.loan_amount.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</span>
              </div>
              <div className="profile-stat-row">
                <span>Transparency:</span>
                <span style={{ color: getVerdictDetails(analysis.transparency.score).color, fontWeight: 700 }}>
                  {analysis.transparency.score}/100
                </span>
              </div>
              <div className="profile-stat-row" style={{ alignItems: 'center', marginTop: 4 }}>
                <span>Risk rating:</span>
                <span 
                  className="risk-badge" 
                  style={{ 
                    color: getVerdictDetails(analysis.transparency.score).color,
                    backgroundColor: getVerdictDetails(analysis.transparency.score).bg
                  }}
                >
                  {getVerdictDetails(analysis.transparency.score).text}
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ background: '#0F1E33', border: '1px dashed rgba(148,163,184,0.15)', borderRadius: 16, padding: 14, marginBottom: 20, textAlign: 'center' }}>
            <div style={{ fontSize: 20, marginBottom: 4 }}>📂</div>
            <div style={{ fontSize: 11, color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase' }}>No Active Loan Audited</div>
            <div style={{ fontSize: 9, color: '#6366F1', marginTop: 4, fontWeight: 600 }}>Upload an agreement to start</div>
          </div>
        )}

        {/* NAVIGATION LINKS */}
        <nav className="sidebar-menu">
          <button className={`menu-item ${activeTab === 'analyze' ? 'active' : ''}`} onClick={() => setActiveTab('analyze')}>
            <span>📂</span> Upload & Analyze
          </button>
          <button className={`menu-item ${activeTab === 'dashboard' ? 'active' : ''}`} onClick={() => setActiveTab('dashboard')}>
            <span>📊</span> Loan Truth Dashboard
          </button>
          <button className={`menu-item ${activeTab === 'charges' ? 'active' : ''}`} onClick={() => setActiveTab('charges')}>
            <span>💸</span> Charges & Penalties
          </button>
          <button className={`menu-item ${activeTab === 'simulator' ? 'active' : ''}`} onClick={() => setActiveTab('simulator')}>
            <span>🧮</span> Payoff Simulator
          </button>
          <button className={`menu-item ${activeTab === 'strategy' ? 'active' : ''}`} onClick={() => setActiveTab('strategy')}>
            <span>⚖️</span> Multi-Debt Strategy
          </button>
          <button className={`menu-item ${activeTab === 'evidence' ? 'active' : ''}`} onClick={() => setActiveTab('evidence')}>
            <span>🔎</span> Verification Evidence
          </button>
          <button className={`menu-item ${activeTab === 'dispute' ? 'active' : ''}`} onClick={() => setActiveTab('dispute')}>
            <span>📧</span> Dispute & Negotiation
          </button>
          <button className={`menu-item ${activeTab === 'report' ? 'active' : ''}`} onClick={() => setActiveTab('report')}>
            <span>📋</span> printable Report
          </button>
          <button className={`menu-item ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>
            <span>💬</span> AI Loan Assistant
          </button>
        </nav>

        {/* BACKEND STATUS INDICATOR */}
        <div style={{ fontSize: 9, padding: '10px 6px', borderTop: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: apiHealth.online ? '#10b981' : '#ef4444', display: 'inline-block' }}></span>
            <span style={{ color: '#cbd5e1', fontWeight: 600 }}>FastAPI Server: {apiHealth.online ? 'Online' : 'Offline'}</span>
          </div>
          {apiHealth.online && (
            <div style={{ color: '#94a3b8', paddingLeft: 14 }}>
              LLM Provider: <b style={{ color: '#38bdf8' }}>{apiHealth.provider.toUpperCase()}</b> ({apiHealth.model})
            </div>
          )}
        </div>

        <div className="sidebar-footer">
          Debt Detox Auditor v2.0
        </div>
      </aside>

      {/* MAIN VIEW AREA */}
      <main className="main-content">
        
        {/* TAB 1: UPLOAD & ANALYZE */}
        {activeTab === 'analyze' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">📂 Document Upload & Analysis Pipeline</h1>
              <p className="page-description">
                Upload your digital loan agreement, credit card terms sheet, or BNPL schedule. Our AI processor will extract terms and verify interest rates.
              </p>
            </header>

            {loading ? (
              <div className="premium-card glow-border-cyan">
                <h3 style={{ marginBottom: 20 }}>⚙️ Execution Pipeline Running</h3>
                <div className="stepper">
                  {[
                    'Processing Document Pages',
                    'Reading Raw Strings & Metadata',
                    'Resolving Scanned Documents (OCR Fallback)',
                    'Extracting Financial Clauses with AI',
                    'Determining Real Amortized Cost (APR)',
                    'Computing Consumer Transparency Metrics'
                  ].map((label, idx) => {
                    const num = idx + 1;
                    const isActive = pipelineStep === num;
                    const isDone = pipelineStep > num;
                    
                    return (
                      <div key={num} className="step-row" style={{ 
                        borderLeft: isActive ? '3.5px solid #38bdf8' : (isDone ? '3.5px solid #10b981' : '1px solid rgba(255,255,255,0.03)'),
                        opacity: isDone || isActive ? 1 : 0.4
                      }}>
                        <span className={`step-badge ${isActive ? 'pulse-step' : ''}`} style={{
                          backgroundColor: isDone ? 'rgba(16,185,129,0.1)' : (isActive ? 'rgba(56,189,248,0.1)' : 'rgba(255,255,255,0.02)'),
                          color: isDone ? '#10b981' : (isActive ? '#38bdf8' : '#94a3b8'),
                          borderColor: isDone ? '#10b981' : (isActive ? '#38bdf8' : 'rgba(255,255,255,0.1)')
                        }}>
                          {isDone ? '✓' : (isActive ? '●' : num)}
                        </span>
                        <span style={{ color: isActive ? '#ffffff' : (isDone ? '#cbd5e1' : '#475569'), fontWeight: isActive ? 600 : 400 }}>{label}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="grid-2">
                <div>
                  <div className="premium-card glow-border-indigo" style={{ padding: 35, textAlign: 'center' }}>
                    <div style={{ fontSize: 44, marginBottom: 15 }}>🛡️</div>
                    <h3 style={{ fontSize: 20, marginBottom: 10 }}>Audit a New Contract</h3>
                    <p style={{ color: '#94a3b8', fontSize: 13, lineHeight: 1.5, marginBottom: 20 }}>
                      Drop a PDF or image of your agreement. Support scanned contracts via automatic OCR.
                    </p>
                    
                    <input 
                      type="file" 
                      id="loan-file" 
                      accept=".pdf,.png,.jpg,.jpeg" 
                      style={{ display: 'none' }} 
                      onChange={handleFileUpload} 
                    />
                    <label htmlFor="loan-file" className="btn" style={{ cursor: 'pointer' }}>
                      📁 Select Agreement File
                    </label>

                    {analysisError && (
                      <div className="premium-card glow-border-rose" style={{ marginTop: 20, padding: 12, fontSize: 12, color: '#ef4444', backgroundColor: 'rgba(239,68,68,0.03)' }}>
                        {analysisError}
                      </div>
                    )}
                  </div>

                  <div className="premium-card glow-border-cyan">
                    <h3 style={{ fontSize: 16, marginBottom: 12 }}>⚡ Try Preloaded Sample Demos</h3>
                    <p style={{ color: '#94a3b8', fontSize: 12, marginBottom: 15 }}>
                      Select a sample file below to inspect instant mock-cached results without needing a live Gemini API key.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <button className="btn btn-secondary" style={{ justifyContent: 'space-between' }} onClick={() => loadSampleDocument('apex_personal_loan_agreement.pdf')}>
                        <span>📄 Apex Personal Loan Agreement</span>
                        <span style={{ fontSize: 10, opacity: 0.8 }}>3.00L Principal / 14.5% Rate</span>
                      </button>
                      <button className="btn btn-secondary" style={{ justifyContent: 'space-between' }} onClick={() => loadSampleDocument('splitpay_bnpl_contract.pdf')}>
                        <span>📄 SplitPay BNPL Promo Contract</span>
                        <span style={{ fontSize: 10, opacity: 0.8 }}>30k Principal / 0% Interest</span>
                      </button>
                      <button className="btn btn-secondary" style={{ justifyContent: 'space-between' }} onClick={() => loadSampleDocument('nova_credit_card_terms.pdf')}>
                        <span>📄 Nova Credit Card Terms Sheet</span>
                        <span style={{ fontSize: 10, opacity: 0.8 }}>15L Credit Limit / 42% APR</span>
                      </button>
                      <button className="btn btn-secondary" style={{ justifyContent: 'space-between' }} onClick={() => loadSampleDocument('scanned_micro_loan_agreement.pdf')}>
                        <span>📄 Scanned QuickMicro Biz Agreement (OCR)</span>
                        <span style={{ fontSize: 10, opacity: 0.8 }}>50k Scanned Loan / 18% Rate</span>
                      </button>
                    </div>
                  </div>
                </div>

                {/* MANUAL CALCULATOR OPTION */}
                <div>
                  <form className="premium-card glow-border-amber" onSubmit={handleManualCalculate}>
                    <h3 style={{ fontSize: 18, marginBottom: 15 }}>🎛️ Manual Parameters Entry</h3>
                    <p style={{ color: '#94a3b8', fontSize: 12, marginBottom: 20 }}>
                      No AI key configured? Enter the loan numbers below directly to compute effective rates, transparency scores, and run simulators.
                    </p>

                    <div className="grid-2">
                      <div className="form-group">
                        <label>Sanctioned Principal Amount (₹)</label>
                        <input 
                          type="number" 
                          value={manualForm.principal} 
                          onChange={(e) => setManualForm(prev => ({ ...prev, principal: parseFloat(e.target.value) || 0 }))} 
                        />
                      </div>
                      <div className="form-group">
                        <label>Stated Interest Rate (% p.a.)</label>
                        <input 
                          type="number" 
                          step="0.1"
                          value={manualForm.interest_rate_annual} 
                          onChange={(e) => setManualForm(prev => ({ ...prev, interest_rate_annual: parseFloat(e.target.value) || 0 }))} 
                        />
                      </div>
                    </div>

                    <div className="grid-2" style={{ marginTop: 8 }}>
                      <div className="form-group">
                        <label>Tenure (Months)</label>
                        <input 
                          type="number" 
                          value={manualForm.tenure_months} 
                          onChange={(e) => setManualForm(prev => ({ ...prev, tenure_months: parseInt(e.target.value) || 0 }))} 
                        />
                      </div>
                      <div className="form-group">
                        <label>Interest Structure Type</label>
                        <select 
                          value={manualForm.interest_type} 
                          onChange={(e) => setManualForm(prev => ({ ...prev, interest_type: e.target.value }))}
                        >
                          <option value="reducing_balance">Reducing Balance (Standard)</option>
                          <option value="flat_rate">Flat Rate Interest</option>
                          <option value="zero_interest">Zero-Interest Promotional</option>
                        </select>
                      </div>
                    </div>

                    <div className="form-group" style={{ marginTop: 8 }}>
                      <label>Stated Monthly EMI (₹) <span style={{ color: '#6366f1', fontSize: 10 }}>(Auto-calculated if empty)</span></label>
                      <input 
                        type="number" 
                        placeholder="e.g. 9984.82"
                        value={manualForm.emi || ''} 
                        onChange={(e) => setManualForm(prev => ({ ...prev, emi: parseFloat(e.target.value) || undefined }))} 
                      />
                    </div>

                    <button type="submit" className="btn" style={{ width: '100%', marginTop: 15 }}>
                      🧮 Compute Financial Metrics
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 2: LOAN TRUTH DASHBOARD */}
        {activeTab === 'dashboard' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">📊 Loan Truth Dashboard</h1>
              <p className="page-description">
                Comprehensive structural audit comparing stated rates against the real effective APR and assessing contract transparency.
              </p>
            </header>

            {!analysis ? (
              <div className="premium-card glow-border-amber" style={{ backgroundColor: 'rgba(245,158,11,0.02)' }}>
                <h4 style={{ color: '#f59e0b', marginBottom: 8 }}>⚠️ No Active Audit Found</h4>
                <p style={{ color: '#cbd5e1', fontSize: 13 }}>Please upload an agreement PDF or load a sample demo file on the <b>Upload & Analyze</b> page.</p>
              </div>
            ) : (
              <div>
                {/* Executive Summary Stats */}
                <div className="active-loan-profile glow-border-indigo" style={{ padding: 18, marginBottom: 24, fontSize: 14 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h4 style={{ fontSize: 16 }}>📄 Document: {analysis.doc_name}</h4>
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                        Category: <b>{analysis.doc_type.toUpperCase()}</b> &nbsp;|&nbsp; Pages: <b>{analysis.total_pages}</b> &nbsp;|&nbsp; Confidence: <b>{analysis.overall_confidence}%</b>
                      </div>
                    </div>
                    <span className="risk-badge" style={{
                      color: getVerdictDetails(analysis.transparency.score).color,
                      backgroundColor: getVerdictDetails(analysis.transparency.score).bg,
                      padding: '5px 12px',
                      borderRadius: 20
                    }}>
                      Audit: {analysis.audit_status}
                    </span>
                  </div>
                </div>

                {/* Core Metrics Cards */}
                <div className="metrics-grid">
                  <div className="premium-card metric-card glow-border-indigo">
                    <div className="metric-label-container">
                      <span className="metric-label">Sanctioned Principal</span>
                      <span className="metric-icon">💰</span>
                    </div>
                    <div className="metric-value">₹{analysis.metrics.loan_amount.toLocaleString('en-IN')}</div>
                  </div>
                  <div className="premium-card metric-card glow-border-cyan">
                    <div className="metric-label-container">
                      <span className="metric-label">Stated Interest Rate</span>
                      <span className="metric-icon">📈</span>
                    </div>
                    <div className="metric-value">{analysis.metrics.interest_rate_annual}% p.a.</div>
                  </div>
                  <div className="premium-card metric-card glow-border-indigo">
                    <div className="metric-label-container">
                      <span className="metric-label">Contract Tenure</span>
                      <span className="metric-icon">📅</span>
                    </div>
                    <div className="metric-value">{analysis.metrics.tenure_months} Months</div>
                  </div>
                  <div className="premium-card metric-card glow-border-emerald">
                    <div className="metric-label-container">
                      <span className="metric-label">Scheduled EMI</span>
                      <span className="metric-icon">💸</span>
                    </div>
                    <div className="metric-value">₹{analysis.metrics.emi.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                  </div>
                </div>

                {/* Borrowing Cost Breakdown ("Truth") */}
                <h3 style={{ fontSize: 18, marginBottom: 15 }}>🔍 The Real Borrowing Cost</h3>
                <div className="reality-grid">
                  <div className="premium-card reality-card glow-border-emerald" style={{ backgroundColor: 'rgba(16,185,129,0.01)' }}>
                    <span className="reality-title">Net Disbursed Amount</span>
                    <div className="reality-value" style={{ color: '#10b981' }}>₹{analysis.metrics.net_disbursed_amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    <p className="reality-desc">What you actually receive in your bank account after upfront fee deductions.</p>
                  </div>
                  <div className="premium-card reality-card glow-border-rose" style={{ backgroundColor: 'rgba(239,68,68,0.01)' }}>
                    <span className="reality-title">Real Scheduled Cost</span>
                    <div className="reality-value" style={{ color: '#ef4444' }}>₹{analysis.metrics.scheduled_total_cost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</div>
                    <p className="reality-desc">The guaranteed markup of this loan. Includes total interest, processing fees, and taxes.</p>
                  </div>
                  <div className="premium-card reality-card glow-border-cyan" style={{ backgroundColor: 'rgba(6,182,212,0.01)' }}>
                    <span className="reality-title">Effective Cost Rate (APR)</span>
                    <div className="reality-value" style={{ color: '#38bdf8' }}>
                      {analysis.effective_rates.effective_annual_cost_rate !== null && analysis.effective_rates.effective_annual_cost_rate !== undefined 
                        ? `${analysis.effective_rates.effective_annual_cost_rate.toFixed(2)}%` 
                        : 'N/A'}
                    </div>
                    <p className="reality-desc">The actual annualized rate taking processing charges, insurance, and tax drag into account.</p>
                  </div>
                </div>

                {/* Stated vs APR Warning */}
                {analysis.effective_rates.effective_annual_cost_rate !== null && 
                 analysis.effective_rates.effective_annual_cost_rate !== undefined && 
                 analysis.effective_rates.effective_annual_cost_rate - analysis.metrics.interest_rate_annual > 0.05 && (
                  <div className="premium-card glow-border-amber" style={{ backgroundColor: 'rgba(245,158,11,0.02)', padding: 15, fontSize: 13, color: '#cbd5e1', marginBottom: 25 }}>
                    ⚠️ <b>The True APR is {(analysis.effective_rates.effective_annual_cost_rate - analysis.metrics.interest_rate_annual).toFixed(2)}% higher</b> than the stated rate of {analysis.metrics.interest_rate_annual}% p.a.
                    This inflation is caused by processing costs and taxes deducted from your sanctioned principal upfront.
                  </div>
                )}

                {/* Score & Evaluation Breakdown */}
                <div className="grid-2">
                  <div className="premium-card" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 25 }}>
                    <span style={{ fontSize: 11, color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700, letterSpacing: '0.05em', marginBottom: 15 }}>Transparency Score</span>
                    
                    {/* SVG Gauge */}
                    <div style={{ position: 'relative', width: 140, height: 140 }}>
                      <svg viewBox="0 0 100 100" className="gauge-svg">
                        <circle cx="50" cy="50" r="40" className="gauge-bg" />
                        <circle 
                          cx="50" 
                          cy="50" 
                          r="40" 
                          className="gauge-fill"
                          stroke={getVerdictDetails(analysis.transparency.score).color}
                          strokeDasharray={`${(analysis.transparency.score / 100) * 251.2} 251.2`}
                        />
                        <text x="50" y="50" className="gauge-value">{analysis.transparency.score}</text>
                      </svg>
                    </div>

                    <div style={{
                      color: getVerdictDetails(analysis.transparency.score).color,
                      backgroundColor: getVerdictDetails(analysis.transparency.score).bg,
                      border: `1px solid rgba(255,255,255,0.05)`,
                      borderRadius: 20,
                      fontWeight: 800,
                      fontSize: 11,
                      padding: '4px 14px',
                      marginTop: 15,
                      textTransform: 'uppercase'
                    }}>
                      {getVerdictDetails(analysis.transparency.score).text}
                    </div>
                    <p style={{ marginTop: 12, fontSize: 12, color: '#cbd5e1', lineHeight: 1.5 }}>
                      {getVerdictDetails(analysis.transparency.score).desc}
                    </p>
                  </div>

                  <div className="premium-card" style={{ padding: 24 }}>
                    <h4 style={{ fontSize: 13, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 15, borderBottom: '1px solid rgba(255,255,255,0.05)', paddingBottom: 10 }}>
                      Evaluation Metrics Breakdown
                    </h4>
                    
                    {[
                      { label: 'Information Completeness', val: analysis.transparency.breakdown.information_completeness, max: 15 },
                      { label: 'Prepayment & Foreclosure Terms', val: analysis.transparency.breakdown.prepayment_conditions, max: 15 },
                      { label: 'Penalty Exposure', val: analysis.transparency.breakdown.penalty_exposure, max: 15 },
                      { label: 'Fee Clarity & Specification', val: analysis.transparency.breakdown.fee_clarity, max: 20 },
                      { label: 'Contract Clarity & Structure', val: analysis.transparency.breakdown.contract_complexity, max: 15 },
                      { label: 'Additional Charges Frequency', val: analysis.transparency.breakdown.additional_charges, max: 20 }
                    ].map((item, index) => {
                      const pct = (item.val / item.max) * 100;
                      return (
                        <div key={index} style={{ marginBottom: 14 }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11.5, marginBottom: 5 }}>
                            <span style={{ color: '#cbd5e1', fontWeight: 600 }}>{item.label}</span>
                            <span style={{ color: '#94a3b8', fontWeight: 700 }}>{item.val} / {item.max}</span>
                          </div>
                          <div style={{ backgroundColor: 'rgba(255,255,255,0.03)', height: 6, borderRadius: 3, overflow: 'hidden' }}>
                            <div style={{ 
                              background: 'linear-gradient(90deg, #6366f1 0%, #38bdf8 100%)', 
                              width: `${pct}%`, 
                              height: '100%', 
                              borderRadius: 3 
                            }}></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Regulatory Compliance Alerts */}
                {analysis.compliance_alerts && analysis.compliance_alerts.length > 0 && (
                  <div style={{ marginTop: 25 }}>
                    <h3 style={{ fontSize: 18, marginBottom: 15, fontFamily: 'var(--font-heading)' }}>⚖️ Regulatory Compliance Alerts</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                      {analysis.compliance_alerts.map((alert, idx) => {
                        const isCritical = alert.severity === 'CRITICAL';
                        const isWarning = alert.severity === 'WARNING';
                        const badgeBg = isCritical ? 'rgba(239, 68, 68, 0.1)' : (isWarning ? 'rgba(245, 158, 11, 0.1)' : 'rgba(99, 102, 241, 0.1)');
                        const badgeColor = isCritical ? '#ef4444' : (isWarning ? '#f59e0b' : '#6366f1');
                        const borderLeftColor = badgeColor;
                        const icon = isCritical ? '🚨' : (isWarning ? '⚠️' : 'ℹ️');
                        
                        return (
                          <div 
                            key={idx} 
                            className="premium-card" 
                            style={{ 
                              padding: 16, 
                              borderLeft: `4px solid ${borderLeftColor}`, 
                              backgroundColor: isCritical ? 'rgba(239, 68, 68, 0.02)' : (isWarning ? 'rgba(245, 158, 11, 0.02)' : 'rgba(99, 102, 241, 0.02)'),
                              marginBottom: 0
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6, flexWrap: 'wrap', gap: 8 }}>
                              <span style={{ fontWeight: 700, color: badgeColor, fontSize: 14, fontFamily: 'var(--font-heading)' }}>
                                {icon} {alert.title}
                              </span>
                              <span style={{ fontSize: 9, background: 'rgba(255,255,255,0.04)', color: '#94a3b8', padding: '2px 8px', borderRadius: 4, fontFamily: 'var(--font-mono)' }}>
                                {alert.law_reference}
                              </span>
                            </div>
                            <div style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.5, marginBottom: 6 }}>
                              {alert.description}
                            </div>
                            <div style={{ fontSize: 12, color: '#94a3b8', fontStyle: 'italic' }}>
                              <b>Impact:</b> {alert.impact}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Loan Amortization Visualizer */}
                <div style={{ marginTop: 30, marginBottom: 25 }}>
                  <h3 style={{ fontSize: 18, marginBottom: 15, fontFamily: 'var(--font-heading)' }}>📈 Loan Amortization Schedule</h3>
                  
                  {(() => {
                    const sched = generateAmortizationSchedule(
                      analysis.metrics.loan_amount,
                      analysis.metrics.interest_rate_annual,
                      analysis.metrics.tenure_months,
                      analysis.metrics.emi
                    );
                    
                    return (
                      <div>
                        {renderDashboardAmortizationTimeline(sched, analysis.metrics.loan_amount)}
                        
                        <div style={{ marginTop: 15 }}>
                          <button 
                            className="btn btn-secondary" 
                            style={{ padding: '6px 14px', fontSize: 12 }}
                            onClick={() => setShowAmortTable(!showAmortTable)}
                          >
                            {showAmortTable ? '▲ Hide' : '▼ View'} Month-by-Month Repayment Breakdown Table
                          </button>
                          
                          {showAmortTable && (
                            <div className="premium-card" style={{ marginTop: 12, padding: 10, maxHeight: 300, overflowY: 'auto' }}>
                              <table>
                                <thead>
                                  <tr>
                                    <th>Month</th>
                                    <th>Scheduled EMI</th>
                                    <th>Interest Repayment</th>
                                    <th>Principal Repayment</th>
                                    <th>Outstanding Balance</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {sched.map((row, rIdx) => (
                                    <tr key={rIdx}>
                                      <td style={{ fontWeight: 700 }}>Month {row.month}</td>
                                      <td>₹{row.emi.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                      <td style={{ color: '#ef4444' }}>₹{row.interest.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                      <td style={{ color: '#10b981' }}>₹{row.principal.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                      <td style={{ fontWeight: 600 }}>₹{row.closing_balance.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 3: CHARGES & PENALTIES */}
        {activeTab === 'charges' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">💸 Charges & Penalty Audits</h1>
              <p className="page-description">
                Deep-dive audit into every fee structure found in the document, classified by timeline and parsed into plain English.
              </p>
            </header>

            {!analysis ? (
              <div className="premium-card glow-border-amber">
                <h4 style={{ color: '#f59e0b', marginBottom: 8 }}>⚠️ No Active Audit Found</h4>
                <p style={{ color: '#cbd5e1', fontSize: 13 }}>Please upload an agreement on the <b>Upload & Analyze</b> tab.</p>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                  <span style={{ fontSize: 11, backgroundColor: 'rgba(99,102,241,0.1)', color: '#818cf8', padding: '3px 8px', borderRadius: 4, fontWeight: 700 }}>
                    BASE & ADDITIONAL FEES (MANDATORY)
                  </span>
                  <span style={{ fontSize: 11, backgroundColor: 'rgba(245,158,11,0.1)', color: '#f59e0b', padding: '3px 8px', borderRadius: 4, fontWeight: 700 }}>
                    CONDITIONAL / PENALTIES (CONTINGENT)
                  </span>
                </div>

                <div className="grid-2">
                  {analysis.charges.map((charge, index) => {
                    const isMandatory = charge.is_mandatory;
                    const val = charge.value;
                    const unit = charge.unit;
                    const basis = charge.basis;
                    const canon = charge.canonical_name;
                    
                    let val_str = 'Not Specified';
                    if (val !== null && val !== undefined) {
                      if (unit === 'percent') val_str = `${val}%`;
                      else if (unit === 'INR') val_str = `₹${val.toLocaleString('en-IN')}`;
                      else val_str = `${val} ${unit}`;
                    }

                    const simpleText = analysis.explanations[canon] || 'Additional fee mentioned in contract.';
                    const mathEx = analysis.math_examples[canon];

                    return (
                      <div 
                        key={index} 
                        className={`premium-card ${isMandatory ? 'glow-border-indigo' : (charge.classification === 'PENALTY' ? 'glow-border-rose' : 'glow-border-amber')}`}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 12 }}>
                          <div>
                            <h4 style={{ fontSize: 15, textTransform: 'capitalize' }}>
                              {charge.original_name || canon.replace(/_/g, ' ')}
                            </h4>
                            <span style={{ 
                              fontSize: 8.5, 
                              fontWeight: 800, 
                              letterSpacing: 0.5, 
                              color: isMandatory ? '#818cf8' : '#f59e0b',
                              textTransform: 'uppercase',
                              display: 'inline-block',
                              marginTop: 4
                            }}>
                              Category: {charge.classification}
                            </span>
                          </div>
                          <span style={{ fontSize: 16, fontWeight: 800, color: '#ffffff', fontFamily: 'var(--font-mono)' }}>
                            {val_str}
                          </span>
                        </div>

                        {/* Plain Language explanation */}
                        <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 8, padding: 12, fontSize: 12.5, color: '#cbd5e1', lineHeight: 1.5, marginBottom: 14 }}>
                          <span style={{ fontWeight: 700, color: '#38bdf8', fontSize: 11, textTransform: 'uppercase', display: 'block', marginBottom: 4 }}>
                            Plain English translation:
                          </span>
                          {simpleText}
                        </div>

                        {/* Math Example */}
                        {mathEx && (
                          <div style={{ fontSize: 11, color: '#94a3b8', borderLeft: '2px solid rgba(56,189,248,0.2)', paddingLeft: 10 }}>
                            <div style={{ textTransform: 'uppercase', fontSize: 9, fontWeight: 700, color: '#38bdf8', marginBottom: 3 }}>
                              Math Example impact:
                            </div>
                            <div>{mathEx.scenario}:</div>
                            <div style={{ fontWeight: 600, color: '#ffffff', marginTop: 2 }}>
                              {mathEx.formula} = <span style={{ color: '#10b981' }}>{typeof mathEx.result === 'number' ? `₹${mathEx.result.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : mathEx.result}</span>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: PAYOFF SIMULATOR */}
        {activeTab === 'simulator' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">🧮 Payoff Acceleration Simulator</h1>
              <p className="page-description">
                Simulate prepayment actions (extra monthly cash or lump sum principal payments) to bypass interest compounds and see how much you save.
              </p>
            </header>

            <div className="grid-2">
              {/* Simulator settings inputs */}
              <div className="premium-card glow-border-indigo" style={{ padding: 20 }}>
                <h4 style={{ fontSize: 14, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', marginBottom: 15 }}>
                  ⚙️ Simulator Settings
                </h4>

                <div className="form-group">
                  <label>Outstanding Balance (₹)</label>
                  <input 
                    type="number" 
                    value={simParams.balance} 
                    onChange={(e) => setSimParams(prev => ({ ...prev, balance: parseFloat(e.target.value) || 0 }))} 
                  />
                </div>

                <div className="grid-2" style={{ gap: 15, margin: '8px 0' }}>
                  <div className="form-group">
                    <label>Stated Interest Rate (% p.a.)</label>
                    <input 
                      type="number" 
                      step="0.1"
                      value={simParams.rate_annual} 
                      onChange={(e) => setSimParams(prev => ({ ...prev, rate_annual: parseFloat(e.target.value) || 0 }))} 
                    />
                  </div>
                  <div className="form-group">
                    <label>Stated Monthly EMI (₹)</label>
                    <input 
                      type="number" 
                      value={simParams.current_emi} 
                      onChange={(e) => setSimParams(prev => ({ ...prev, current_emi: parseFloat(e.target.value) || 0 }))} 
                    />
                  </div>
                </div>

                <h4 style={{ fontSize: 14, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em', margin: '20px 0 15px 0' }}>
                  🚀 Prepayment Strategy
                </h4>

                <div className="slider-container" style={{ marginBottom: 15 }}>
                  <div className="slider-header">
                    <span>Extra Monthly Payment</span>
                    <span style={{ color: '#10b981', fontWeight: 700 }}>₹{simParams.extra_monthly}</span>
                  </div>
                  <input 
                    type="range" 
                    min="0" 
                    max={simParams.current_emi * 2} 
                    step="100" 
                    value={simParams.extra_monthly} 
                    onChange={(e) => setSimParams(prev => ({ ...prev, extra_monthly: parseFloat(e.target.value) || 0 }))} 
                  />
                </div>

                <div className="grid-2" style={{ gap: 15 }}>
                  <div className="form-group">
                    <label>One-time Lump Sum (₹)</label>
                    <input 
                      type="number" 
                      value={simParams.one_time_payment} 
                      onChange={(e) => setSimParams(prev => ({ ...prev, one_time_payment: parseFloat(e.target.value) || 0 }))} 
                    />
                  </div>
                  <div className="form-group">
                    <label>Lump Sum Paid on Month</label>
                    <input 
                      type="number" 
                      min="1"
                      value={simParams.one_time_month} 
                      onChange={(e) => setSimParams(prev => ({ ...prev, one_time_month: parseInt(e.target.value) || 1 }))} 
                    />
                  </div>
                </div>
              </div>

              {/* Simulation metrics & graph */}
              {simResult ? (
                <div>
                  <div className="premium-card glow-border-emerald" style={{ padding: 20 }}>
                    <div style={{ fontSize: 11, color: '#94A3B8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 15 }}>
                      🚀 Prepayment Impact Assessment
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 15 }}>
                      <div>
                        <div style={{ fontSize: 10, color: '#94A3B8', fontWeight: 700 }}>YOU COULD SAVE</div>
                        <h2 style={{ fontSize: 32, color: '#10B981', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>
                          ₹{simResult.interest_saved.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </h2>
                        <span style={{ background: 'rgba(16, 185, 129, 0.1)', color: '#10B981', fontSize: 9, fontWeight: 800, padding: '3px 8px', borderRadius: 4, display: 'inline-block', marginTop: 6 }}>
                          {((simResult.interest_saved / (simResult.normal_total_interest || 1)) * 100).toFixed(1)}% INTERST CUT
                        </span>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: 10, color: '#94A3B8', fontWeight: 700 }}>PAYOFF ACCELERATION</div>
                        <h2 style={{ fontSize: 32, color: '#38BDF8', fontWeight: 800, fontFamily: 'var(--font-heading)' }}>
                          {simResult.months_saved} <span style={{ fontSize: 18, fontWeight: 500, color: '#cbd5e1' }}>Months</span>
                        </h2>
                        <span style={{ background: 'rgba(56, 189, 248, 0.1)', color: '#38BDF8', fontSize: 9, fontWeight: 800, padding: '3px 8px', borderRadius: 4, display: 'inline-block', marginTop: 6 }}>
                          CLOSE IN {simResult.accelerated_months} MONTHS
                        </span>
                      </div>
                    </div>

                    <div style={{ borderTop: '1px solid rgba(148,163,184,0.12)', marginTop: 15, paddingTop: 12, display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, textAlign: 'center', fontSize: 11.5 }}>
                      <div>
                        <div style={{ color: '#94A3B8' }}>Normal Term</div>
                        <div style={{ fontWeight: 700, color: '#ffffff', marginTop: 2 }}>{simResult.normal_months} Months</div>
                      </div>
                      <div>
                        <div style={{ color: '#94A3B8' }}>Accelerated Term</div>
                        <div style={{ fontWeight: 700, color: '#38BDF8', marginTop: 2 }}>{simResult.accelerated_months} Months</div>
                      </div>
                      <div>
                        <div style={{ color: '#94A3B8' }}>Total Cash Saving</div>
                        <div style={{ fontWeight: 700, color: '#10b981', marginTop: 2 }}>
                          ₹{simResult.interest_saved.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Paydown timeline chart */}
                  <h4 style={{ fontSize: 13, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '15px 0 8px 0' }}>
                    📈 Balance Paydown Timeline
                  </h4>
                  {renderAmortizationTimeline()}
                </div>
              ) : (
                <div className="premium-card glow-border-amber">
                  <h4>Running simulation...</h4>
                </div>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: DEBT STRATEGY COMPARISON */}
        {activeTab === 'strategy' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">⚖️ Multi-Debt Strategy comparison</h1>
              <p className="page-description">
                Manage multiple outstanding debts. Prioritize repayment schedules using Avalanche (highest interest cost) vs. Snowball (psychological cash flow wins) strategies.
              </p>
            </header>

            {/* Strategy Sub-tabs */}
            <div style={{ display: 'flex', gap: 15, borderBottom: '1px solid rgba(255,255,255,0.08)', marginBottom: 25 }}>
              <button 
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: strategySubTab === 'roadmap' ? '#38bdf8' : '#94a3b8',
                  borderBottom: strategySubTab === 'roadmap' ? '2.5px solid #38bdf8' : 'none',
                  padding: '10px 16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  fontSize: 14,
                  transition: 'all 0.2s'
                }}
                onClick={() => setStrategySubTab('roadmap')}
              >
                ⚖️ Repayment Priority Roadmap
              </button>
              <button 
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: strategySubTab === 'matrix' ? '#38bdf8' : '#94a3b8',
                  borderBottom: strategySubTab === 'matrix' ? '2.5px solid #38bdf8' : 'none',
                  padding: '10px 16px',
                  fontWeight: 'bold',
                  cursor: 'pointer',
                  fontSize: 14,
                  transition: 'all 0.2s'
                }}
                onClick={() => setStrategySubTab('matrix')}
              >
                📊 Side-by-Side Loan Comparison Matrix
              </button>
            </div>

            {strategySubTab === 'roadmap' ? (
              <div className="grid-2">
                {/* Debt list card */}
                <div className="premium-card glow-border-indigo" style={{ padding: 20 }}>
                  <div style={{ display: 'flex', justifycontent: 'space-between', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
                    <h4 style={{ fontSize: 14, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                      ⚙️ Your Amortization Catalog
                    </h4>
                    <button className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: 11 }} onClick={addManualDebt}>
                      ➕ Add Debt
                    </button>
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {debts.map((d, index) => (
                      <div key={d.id} style={{ background: 'rgba(255,255,255,0.015)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 10, padding: 12 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                          <input 
                            type="text" 
                            value={d.name} 
                            style={{ fontWeight: 700, padding: '4px 8px', width: '70%', background: 'rgba(0,0,0,0.1)', border: 'none' }}
                            onChange={(e) => {
                              const newName = e.target.value;
                              setDebts(prev => prev.map(item => item.id === d.id ? { ...item, name: newName } : item));
                            }} 
                          />
                          <button style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 13 }} onClick={() => removeDebt(d.id)}>
                            ✕ Delete
                          </button>
                        </div>

                        <div className="grid-3" style={{ gap: 10 }}>
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: 9 }}>Balance (₹)</label>
                            <input 
                              type="number" 
                              style={{ padding: '6px 8px', fontSize: 12 }}
                              value={d.balance} 
                              onChange={(e) => updateDebtItem(d.id, 'balance', e.target.value)} 
                            />
                          </div>
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: 9 }}>Interest Rate (%)</label>
                            <input 
                              type="number" 
                              step="0.1"
                              style={{ padding: '6px 8px', fontSize: 12 }}
                              value={d.interest_rate} 
                              onChange={(e) => updateDebtItem(d.id, 'interest_rate', e.target.value)} 
                            />
                          </div>
                          <div className="form-group" style={{ marginBottom: 0 }}>
                            <label style={{ fontSize: 9 }}>Monthly EMI (₹)</label>
                            <input 
                              type="number" 
                              style={{ padding: '6px 8px', fontSize: 12 }}
                              value={d.emi} 
                              onChange={(e) => updateDebtItem(d.id, 'emi', e.target.value)} 
                            />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Priority Strategy results */}
                <div>
                  <div className="premium-card glow-border-cyan" style={{ padding: 20, marginBottom: 20 }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
                      <h4 style={{ fontSize: 12, textTransform: 'uppercase', color: '#94a3b8', letterSpacing: '0.05em' }}>
                        ⚖️ Select Paydown Strategy
                      </h4>
                      
                      <select 
                        style={{ width: 'auto', padding: '6px 10px', fontSize: 12 }}
                        value={strategy}
                        onChange={(e) => setStrategy(e.target.value)}
                      >
                        <option value="avalanche">Debt Avalanche (Mathematically Optimal)</option>
                        <option value="snowball">Debt Snowball (Smallest Debt First)</option>
                        <option value="ai_recommended">AI recommended (Hybrid Cost/Momentum)</option>
                      </select>
                    </div>

                    {strategyResult && (
                      <div>
                        <h3 style={{ color: '#38bdf8', fontSize: 16, marginBottom: 6 }}>
                          {strategyResult.explanation.title}
                        </h3>
                        <p style={{ fontSize: 12, color: '#cbd5e1', lineHeight: 1.5, marginBottom: 12 }}>
                          {strategyResult.explanation.mechanism}
                        </p>
                        
                        <div style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.03)', borderRadius: 8, padding: 10, fontSize: 11.5, color: '#cbd5e1', marginBottom: 10 }}>
                          <span style={{ color: '#10b981', fontWeight: 700, display: 'block', marginBottom: 2 }}>PROS:</span>
                          {strategyResult.explanation.pros}
                        </div>

                        <div style={{ fontSize: 11, color: '#94a3b8', fontStyle: 'italic' }}>
                          💡 <b>Recommendation Advice:</b> {strategyResult.explanation.advice}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Priority order list */}
                  <h4 style={{ fontSize: 13, color: '#ffffff', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                    🎯 Priority Repayment Sequence Order
                  </h4>
                  
                  {strategyResult && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                      {strategyResult.debts.map((item, index) => {
                        const glowColor = index === 0 ? '#10b981' : (index === debts.length - 1 ? 'rgba(255,255,255,0.08)' : '#818cf8');
                        const borderLeftStyle = index === 0 ? '4px solid #10b981' : '4px solid rgba(255,255,255,0.1)';
                        
                        return (
                          <div key={index} className="premium-card" style={{ padding: 12, borderLeft: borderLeftStyle, marginBottom: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                              <span style={{ 
                                width: 22, 
                                height: 22, 
                                borderRadius: '50%', 
                                backgroundColor: index === 0 ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.03)',
                                color: index === 0 ? '#10b981' : '#94a3b8',
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifycontent: 'center',
                                justifyContent: 'center',
                                fontWeight: 'bold',
                                fontSize: 11
                              }}>
                                {item.priority_rank}
                              </span>
                              <div>
                                <div style={{ fontWeight: 700, color: '#ffffff', fontSize: 13.5 }}>{item.name}</div>
                                <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                                  Balance: ₹{item.balance.toLocaleString('en-IN')} &nbsp;|&nbsp; Rate: {item.interest_rate}% p.a.
                                </div>
                              </div>
                            </div>

                            <div style={{ textAlign: 'right' }}>
                              <span style={{ 
                                fontSize: 9, 
                                fontWeight: 800, 
                                padding: '2px 8px', 
                                borderRadius: 12, 
                                backgroundColor: index === 0 ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.02)',
                                color: index === 0 ? '#10b981' : '#94a3b8' 
                              }}>
                                {index === 0 ? '🔥 ACTIVE TARGET' : 'QUEUED'}
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div>
                {/* Comparison Matrix view */}
                <h3 style={{ fontSize: 18, marginBottom: 15, fontFamily: 'var(--font-heading)' }}>⚖️ Side-by-Side Loan Offers Comparison</h3>
                <p style={{ color: '#94a3b8', fontSize: 12.5, marginBottom: 20, lineHeight: 1.5 }}>
                  Compare different loan parameters (processing fees, nominal rates, insurance) side-by-side. The matrix computes the actual Effective APR drag and total cost of borrowing on the fly.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 18, marginBottom: 25 }}>
                  {compLoans.map((loan, lIdx) => (
                    <div key={lIdx} className="premium-card glow-border-indigo" style={{ padding: 20, marginBottom: 0 }}>
                      <h4 style={{ color: '#38bdf8', fontSize: 15, marginBottom: 15, textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                        {loan.name}
                      </h4>
                      
                      <div className="form-group">
                        <label>Principal Loan Amount (₹)</label>
                        <input 
                          type="number" 
                          value={loan.principal} 
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 0;
                            setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, principal: val, emi: Math.round(calculateReducingEmi(val, item.interestRate, item.tenure)) } : item));
                          }}
                        />
                      </div>
                      
                      <div className="grid-2" style={{ gap: 10, marginTop: 8 }}>
                        <div className="form-group">
                          <label>Interest Rate (% p.a.)</label>
                          <input 
                            type="number" 
                            step="0.1"
                            value={loan.interestRate} 
                            onChange={(e) => {
                              const val = parseFloat(e.target.value) || 0;
                              setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, interestRate: val, emi: Math.round(calculateReducingEmi(item.principal, val, item.tenure)) } : item));
                            }}
                          />
                        </div>
                        <div className="form-group">
                          <label>Tenure (Months)</label>
                          <input 
                            type="number" 
                            value={loan.tenure} 
                            onChange={(e) => {
                              const val = parseInt(e.target.value) || 0;
                              setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, tenure: val, emi: Math.round(calculateReducingEmi(item.principal, item.interestRate, val)) } : item));
                            }}
                          />
                        </div>
                      </div>

                      <div className="grid-2" style={{ gap: 10, marginTop: 8 }}>
                        <div className="form-group">
                          <label>Processing Fee (%)</label>
                          <input 
                            type="number" 
                            step="0.1"
                            value={loan.pf} 
                            onChange={(e) => {
                              const val = parseFloat(e.target.value) || 0;
                              setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, pf: val } : item));
                            }}
                          />
                        </div>
                        <div className="form-group">
                          <label>Insurance Cover (₹)</label>
                          <input 
                            type="number" 
                            value={loan.ins} 
                            onChange={(e) => {
                              const val = parseFloat(e.target.value) || 0;
                              setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, ins: val } : item));
                            }}
                          />
                        </div>
                      </div>

                      <div className="form-group" style={{ marginTop: 8 }}>
                        <label>Monthly EMI (₹)</label>
                        <input 
                          type="number" 
                          value={loan.emi} 
                          onChange={(e) => {
                            const val = parseFloat(e.target.value) || 0;
                            setCompLoans(prev => prev.map((item, idx) => idx === lIdx ? { ...item, emi: val } : item));
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Comparison Matrix Table */}
                <h3 style={{ fontSize: 16, marginBottom: 15, fontFamily: 'var(--font-heading)' }}>📊 Derived Comparison Matrix</h3>
                <div className="premium-card" style={{ padding: 12, overflowX: 'auto' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Comparison Metric</th>
                        {compLoans.map((loan, idx) => <th key={idx}>{loan.name}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {(() => {
                        const calculated = compLoans.map(loan => {
                          const pfVal = loan.principal * (loan.pf / 100.0);
                          const gstVal = pfVal * 0.18;
                          const upfrontLeakage = pfVal + gstVal + loan.ins;
                          const netDisbursed = loan.principal - upfrontLeakage;
                          
                          const totalRepayments = loan.emi * loan.tenure;
                          const totalInterest = Math.max(0, totalRepayments - loan.principal);
                          const totalBorrowingCost = totalInterest + upfrontLeakage;
                          
                          const apr = calculateEffectiveAprJS(netDisbursed, loan.emi, loan.tenure);
                          
                          return {
                            principal: loan.principal,
                            statedRate: loan.interestRate,
                            tenure: loan.tenure,
                            emi: loan.emi,
                            pfVal,
                            gstVal,
                            netDisbursed,
                            totalInterest,
                            totalBorrowingCost,
                            apr
                          };
                        });

                        return (
                          <>
                            <tr>
                              <td style={{ fontWeight: 700 }}>Sanctioned Principal</td>
                              {calculated.map((c, idx) => <td key={idx}>₹{c.principal.toLocaleString('en-IN')}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>Stated Nominal Rate</td>
                              {calculated.map((c, idx) => <td key={idx}>{c.statedRate}% p.a.</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>Contract Tenure</td>
                              {calculated.map((c, idx) => <td key={idx}>{c.tenure} Months</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>Monthly EMI</td>
                              {calculated.map((c, idx) => <td key={idx}>₹{c.emi.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700, color: '#38bdf8' }}>Net Disbursed Amount</td>
                              {calculated.map((c, idx) => <td key={idx} style={{ color: '#38bdf8', fontWeight: 'bold' }}>₹{c.netDisbursed.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>Upfront Processing Fee</td>
                              {calculated.map((c, idx) => <td key={idx}>₹{c.pfVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>GST / Tax on Fees</td>
                              {calculated.map((c, idx) => <td key={idx}>₹{c.gstVal.toLocaleString('en-IN', { maximumFractionDigits: 0 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700, color: '#ef4444' }}>Total Interest Payable</td>
                              {calculated.map((c, idx) => <td key={idx} style={{ color: '#ef4444' }}>₹{c.totalInterest.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700, color: '#f59e0b' }}>Total Borrowing Cost</td>
                              {calculated.map((c, idx) => <td key={idx} style={{ color: '#f59e0b', fontWeight: 'bold' }}>₹{c.totalBorrowingCost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700, color: '#10b981' }}>Effective Annual APR</td>
                              {calculated.map((c, idx) => <td key={idx} style={{ color: '#10b981', fontWeight: 'bold', fontSize: 14 }}>{c.apr.toFixed(2)}% p.a.</td>)}
                            </tr>
                            <tr>
                              <td style={{ fontWeight: 700 }}>APR Markup Over Stated</td>
                              {calculated.map((c, idx) => {
                                const diff = c.apr - c.statedRate;
                                return <td key={idx} style={{ color: diff > 2 ? '#ef4444' : '#cbd5e1' }}>+{diff.toFixed(2)}%</td>;
                              })}
                            </tr>
                          </>
                        );
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 6: VERIFICATION EVIDENCE */}
        {activeTab === 'evidence' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">🔎 Verification Trace Lockers</h1>
              <p className="page-description">
                100% auditability trail. Every extracted rate and fee mapped to the exact page number and text snippet quote extracted from the original PDF contract.
              </p>
            </header>

            {!analysis ? (
              <div className="premium-card glow-border-amber">
                <h4 style={{ color: '#f59e0b', marginBottom: 8 }}>⚠️ No Active Audit Found</h4>
                <p style={{ color: '#cbd5e1', fontSize: 13 }}>Please upload an agreement on the <b>Upload & Analyze</b> tab.</p>
              </div>
            ) : (
              <div className="premium-card" style={{ padding: 10 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Term Mapped</th>
                      <th>Extracted Value</th>
                      <th style={{ width: '10%' }}>Page #</th>
                      <th>Verbatim Supporting Text Quote Quote (Contract Evidence)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analysis.charges.map((item, index) => {
                      const val = item.value;
                      const unit = item.unit;
                      let val_str = 'Not Specified';
                      if (val !== null && val !== undefined) {
                        if (unit === 'percent') val_str = `${val}%`;
                        else if (unit === 'INR') val_str = `₹${val.toLocaleString('en-IN')}`;
                        else val_str = `${val} ${unit}`;
                      }

                      return (
                        <tr key={index}>
                          <td style={{ fontWeight: 700, color: '#38bdf8', textTransform: 'capitalize' }}>
                            {item.original_name || item.canonical_name.replace(/_/g, ' ')}
                          </td>
                          <td style={{ fontWeight: 800, fontFamily: 'var(--font-mono)' }}>{val_str}</td>
                          <td style={{ color: '#38bdf8', fontWeight: 'bold' }}>{item.page || 1}</td>
                          <td style={{ fontSize: 12.5, color: '#cbd5e1', fontStyle: 'italic', lineHeight: 1.5, fontFamily: 'var(--font-heading)' }}>
                            "{item.evidence}"
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 7: DISPUTE & NEGOTIATION LETTER */}
        {activeTab === 'dispute' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">📧 Dispute & Negotiation Letter Generator</h1>
              <p className="page-description">
                Generate an automated, legally-grounded fee waiver & contract renegotiation letter based on extracted loan terms and compliance findings.
              </p>
            </header>

            {!analysis ? (
              <div className="premium-card glow-border-amber">
                <h4 style={{ color: '#f59e0b', marginBottom: 8 }}>⚠️ No Active Audit Found</h4>
                <p style={{ color: '#cbd5e1', fontSize: 13 }}>Please upload an agreement on the <b>Upload & Analyze</b> tab.</p>
              </div>
            ) : (
              <div className="grid-2" style={{ gridTemplateColumns: '1fr 1.2fr', gap: 20 }}>
                {/* Column 1: Config */}
                <div className="premium-card glow-border-indigo" style={{ padding: 20 }}>
                  <h3 style={{ fontSize: 16, color: '#38bdf8', marginBottom: 15 }}>1. Customize Letter Parameters</h3>
                  
                  <div className="form-group">
                    <label>Borrower Full Name:</label>
                    <input 
                      type="text" 
                      value={disputeBorrowerName} 
                      onChange={(e) => setDisputeBorrowerName(e.target.value)} 
                    />
                  </div>

                  <div style={{ marginTop: 15, fontWeight: 600, color: '#cbd5e1', fontSize: 13, marginBottom: 10 }}>
                    Select Disputed Charges to Include:
                  </div>

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, maxHeight: 220, overflowY: 'auto', paddingRight: 5 }}>
                    {(analysis.charges || []).map((c, idx) => {
                      const canon = c.canonical_name;
                      const isChecked = disputeSelectedCharges.includes(canon);
                      const val = c.value;
                      const unit = c.unit;
                      let val_str = 'Not Specified';
                      if (val !== null && val !== undefined) {
                        if (unit === 'percent') val_str = `${val}%`;
                        else if (unit === 'INR') val_str = `₹${val.toLocaleString('en-IN')}`;
                        else val_str = `${val} ${unit}`;
                      }

                      return (
                        <label key={idx} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12.5, color: '#cbd5e1', cursor: 'pointer' }}>
                          <input 
                            type="checkbox" 
                            checked={isChecked}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setDisputeSelectedCharges(prev => [...prev, canon]);
                              } else {
                                setDisputeSelectedCharges(prev => prev.filter(x => x !== canon));
                              }
                            }}
                          />
                          <span>{c.original_name || canon.replace(/_/g, ' ')} <b style={{ color: '#38bdf8' }}>({val_str})</b></span>
                        </label>
                      );
                    })}
                  </div>

                  <div className="form-group" style={{ marginTop: 15 }}>
                    <label>Additional Notes / Specific Requests:</label>
                    <textarea 
                      rows="3"
                      placeholder="e.g., I have maintained a salary account with your bank for 5 years and request an executive relationship waiver."
                      value={disputeCustomNotes}
                      onChange={(e) => setDisputeCustomNotes(e.target.value)}
                      style={{ width: '100%', padding: '8px 12px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(0,0,0,0.2)', color: '#ffffff', fontSize: 12 }}
                    />
                  </div>
                </div>

                {/* Column 2: Live Notice Preview */}
                <div>
                  <h3 style={{ fontSize: 16, color: '#10b981', marginBottom: 15 }}>2. Generated Formal Notice Preview</h3>
                  
                  <div style={{
                    background: '#07111F',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    borderRadius: 12,
                    padding: 20,
                    maxHeight: 460,
                    overflowY: 'auto',
                    fontFamily: 'monospace',
                    fontSize: 12,
                    lineHeight: 1.6,
                    color: '#F8FAFC',
                    whiteSpace: 'pre-wrap',
                    marginBottom: 15,
                    boxShadow: 'inset 0 2px 10px rgba(0,0,0,0.5)'
                  }}>
                    {generateDisputeLetterText()}
                  </div>

                  <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                    <button 
                      className="btn"
                      onClick={() => {
                        const element = document.createElement("a");
                        const file = new Blob([generateDisputeLetterText()], { type: 'text/plain' });
                        element.href = URL.createObjectURL(file);
                        element.download = `Dispute_Notice_${(analysis.doc_name || 'Loan').replace(/\s+/g, '_')}.txt`;
                        document.body.appendChild(element);
                        element.click();
                        document.body.removeChild(element);
                      }}
                    >
                      📥 Download Notice (.txt)
                    </button>
                    <span style={{ fontSize: 11, color: '#94a3b8' }}>
                      💡 Copy the notice text above and submit via registered email to your lender's grievance desk.
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 7: printable REPORT VIEW */}
        {activeTab === 'report' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">📋 printable Summary Report</h1>
              <p className="page-description">
                Generate and export a clean print layout of this AI borrowing costs audit.
              </p>
            </header>

            {!analysis ? (
              <div className="premium-card glow-border-amber">
                <h4 style={{ color: '#f59e0b', marginBottom: 8 }}>⚠️ No Active Audit Found</h4>
                <p style={{ color: '#cbd5e1', fontSize: 13 }}>Please upload an agreement on the <b>Upload & Analyze</b> tab.</p>
              </div>
            ) : (
              <div>
                <div style={{ display: 'flex', gap: 10, marginBottom: 20 }}>
                  <button className="btn" onClick={() => window.print()}>
                    🖨️ Open Print Options
                  </button>
                </div>

                {/* Printable Frame wrapper */}
                <div className="premium-card" style={{ padding: 40, border: '1px solid rgba(255,255,255,0.06)', background: '#0F1E33', color: '#ffffff' }}>
                  <div style={{ borderBottom: '2px solid rgba(56,189,248,0.2)', paddingBottom: 15, marginBottom: 25, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <h2 style={{ fontSize: 24, margin: 0, color: '#ffffff' }}>DEBT DETOX AUDIT REPORT</h2>
                      <div style={{ color: '#94a3b8', fontSize: 11, marginTop: 4 }}>
                        LENDER: {analysis.charges.find(c => c.canonical_name === 'lender_name')?.value || 'Apex Lending Services'}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontSize: 12, fontWeight: 'bold', color: '#10b981' }}>VERIFIED AUDIT STATUS</div>
                      <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>Date Checked: {new Date().toLocaleDateString()}</div>
                    </div>
                  </div>

                  <div className="grid-2" style={{ gap: 30, marginBottom: 30 }}>
                    <div>
                      <h4 style={{ color: '#38bdf8', marginBottom: 12, fontSize: 12, textTransform: 'uppercase' }}>Loan Core Specifications</h4>
                      <table style={{ border: 'none' }}>
                        <tbody>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Borrower Name</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold' }}>{analysis.charges.find(c => c.canonical_name === 'borrower_name')?.value || 'John Doe'}</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Sanctioned Principal</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold' }}>₹{analysis.metrics.loan_amount.toLocaleString('en-IN')}</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Stated Nominal Rate</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold' }}>{analysis.metrics.interest_rate_annual}% p.a.</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Contracted Tenure</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold' }}>{analysis.metrics.tenure_months} Months</td></tr>
                        </tbody>
                      </table>
                    </div>

                    <div>
                      <h4 style={{ color: '#38bdf8', marginBottom: 12, fontSize: 12, textTransform: 'uppercase' }}>Audited Cost Reality Summary</h4>
                      <table style={{ border: 'none' }}>
                        <tbody>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Net Disbursed Amount</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold', color: '#10b981' }}>₹{analysis.metrics.net_disbursed_amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Real Amortized APR</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold', color: '#38bdf8' }}>{analysis.effective_rates.effective_annual_cost_rate !== null && analysis.effective_rates.effective_annual_cost_rate !== undefined ? `${analysis.effective_rates.effective_annual_cost_rate.toFixed(2)}%` : 'N/A'}</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Total Guaranteed Cost</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold', color: '#ef4444' }}>₹{analysis.metrics.scheduled_total_cost.toLocaleString('en-IN', { maximumFractionDigits: 2 })}</td></tr>
                          <tr style={{ background: 'none' }}><td style={{ padding: '6px 0', border: 'none', color: '#94a3b8' }}>Transparency score</td><td style={{ padding: '6px 0', border: 'none', fontWeight: 'bold' }}>{analysis.transparency.score} / 100</td></tr>
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <h4 style={{ color: '#38bdf8', marginBottom: 12, fontSize: 12, textTransform: 'uppercase' }}>Audited Additional Charges Listing</h4>
                  <table style={{ marginBottom: 30 }}>
                    <thead>
                      <tr>
                        <th>Fee Type</th>
                        <th>Extracted Rate</th>
                        <th>Classification</th>
                        <th>Timeline Type</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.charges.map((c, idx) => {
                        const val = c.value;
                        const unit = c.unit;
                        let val_str = 'Not Specified';
                        if (val !== null && val !== undefined) {
                          if (unit === 'percent') val_str = `${val}%`;
                          else if (unit === 'INR') val_str = `₹${val.toLocaleString('en-IN')}`;
                          else val_str = `${val} ${unit}`;
                        }
                        
                        return (
                          <tr key={idx}>
                            <td style={{ textTransform: 'capitalize' }}>{c.original_name || c.canonical_name.replace(/_/g, ' ')}</td>
                            <td>{val_str}</td>
                            <td>{c.classification}</td>
                            <td>{c.is_mandatory ? 'Upfront/Scheduled' : 'Contingent Penalty'}</td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>

                  <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 15, fontSize: 11, color: '#94a3b8', textAlign: 'center' }}>
                    Disclaimer: This audit report was compiled using Debt Detox financial literacy analysis engine. 
                    Calculations are based strictly on data extracted from the uploaded document template.
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB 8: AI LOAN ASSISTANT CHATBOT */}
        {activeTab === 'chat' && (
          <div>
            <header className="page-header">
              <h1 className="page-title">💬 Interactive AI Loan Assistant</h1>
              <p className="page-description">
                Ask specific questions about your agreement clauses, penalties, lock-in terms, or transparency scoring.
              </p>
            </header>

            <div className="premium-card glow-border-cyan" style={{ padding: 20, display: 'flex', flexDirection: 'column', height: '65vh', marginBottom: 0 }}>
              {/* Message History list */}
              <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 15, paddingRight: 5 }}>
                {chatMessages.map((msg, index) => {
                  const isUser = msg.role === 'user';
                  return (
                    <div 
                      key={index} 
                      style={{ 
                        alignSelf: isUser ? 'flex-end' : 'flex-start',
                        maxWidth: '75%',
                        backgroundColor: isUser ? '#6366f1' : 'rgba(255,255,255,0.03)',
                        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        borderRadius: 12,
                        padding: '12px 16px',
                        fontSize: 13.5,
                        color: '#ffffff',
                        lineHeight: 1.5
                      }}
                    >
                      <div style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', color: isUser ? '#c7d2fe' : '#38bdf8', marginBottom: 4 }}>
                        {isUser ? 'You' : 'AI Assistant'}
                      </div>
                      <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                    </div>
                  );
                })}
                {chatLoading && (
                  <div style={{ alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.01)', borderRadius: 12, padding: '12px 16px', fontSize: 13, color: '#94a3b8' }}>
                    🤖 <i>AI is scanning your agreement terms...</i>
                  </div>
                )}
              </div>

              {/* Chat inputs bar */}
              <div style={{ display: 'flex', gap: 10 }}>
                <input 
                  type="text" 
                  placeholder={analysis ? "Ask about late fees, prepayment limits, hidden costs..." : "Please upload a document to unlock contract-specific Q&A"}
                  disabled={chatLoading}
                  value={chatInput} 
                  onChange={(e) => setChatInput(e.target.value)} 
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSendChatMessage();
                  }}
                  style={{ flex: 1, padding: '10px 16px', borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(0,0,0,0.2)', color: '#ffffff' }}
                />
                <button 
                  className="btn btn-primary" 
                  disabled={chatLoading || !chatInput.trim()}
                  onClick={handleSendChatMessage}
                  style={{ padding: '10px 22px' }}
                >
                  Send
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
