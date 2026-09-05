import axios from 'axios';

const API_BASE_URL = '/api';

export const checkHealth = async () => {
  const response = await axios.get(`${API_BASE_URL}/health`);
  return response.data;
};

export const fetchPatients = async () => {
  const response = await axios.get(`${API_BASE_URL}/patients`);
  return response.data.patients || [];
};

export const createPatient = async (patientId) => {
  const response = await axios.post(`${API_BASE_URL}/patients`, {
    patient_id: patientId
  });
  return response.data;
};

export const deletePatient = async (patientId) => {
  const response = await axios.delete(`${API_BASE_URL}/patients/${encodeURIComponent(patientId)}`);
  return response.data;
};

export const clearAllPatients = async () => {
  const response = await axios.delete(`${API_BASE_URL}/patients`);
  return response.data;
};

export const uploadFiles = async (patientId, files) => {
  const formData = new FormData();
  formData.append('patient_id', patientId);
  for (let i = 0; i < files.length; i++) {
    formData.append('files', files[i]);
  }

  const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const sendChatMessage = async (patientId, question) => {
  const response = await axios.post(`${API_BASE_URL}/chat`, {
    patient_id: patientId,
    question: question,
  });
  return response.data;
};

export const fetchPatientDocuments = async (patientId) => {
  const response = await axios.get(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/documents`);
  return response.data;
};

// Clinical Analytics API Endpoints
export const fetchPatientLabs = async (patientId) => {
  const response = await axios.get(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/labs`);
  return response.data;
};

export const fetchPatientTimeline = async (patientId) => {
  const response = await axios.get(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/timeline`);
  return response.data;
};

export const generateClinicalSummary = async (patientId) => {
  const response = await axios.post(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/summarize`);
  return response.data;
};

export const checkDrugSafety = async (patientId, proposedDrug) => {
  const response = await axios.post(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/safety-check`, {
    proposed_drug: proposedDrug
  });
  return response.data;
};

export const fetchPatientRiskCalculator = async (patientId) => {
  const response = await axios.get(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/risk-calculator`);
  return response.data;
};

export const fetchPatientFhirBundle = async (patientId) => {
  const response = await axios.get(`${API_BASE_URL}/patient/${encodeURIComponent(patientId)}/fhir`);
  return response.data;
};

export const submitFeedback = async (auditId, rating, comment = '') => {
  const response = await axios.post(`${API_BASE_URL}/feedback`, {
    audit_id: auditId,
    rating: rating,
    comment: comment
  });
  return response.data;
};

export const fetchAuditLogs = async (limit = 50) => {
  const response = await axios.get(`${API_BASE_URL}/audit-logs?limit=${limit}`);
  return response.data;
};
