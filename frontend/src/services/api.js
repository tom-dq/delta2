import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

class DeltaAPI {
  constructor() {
    this.sessionId = this.generateSessionId();
    this.axios = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
    });
  }

  generateSessionId() {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  async healthCheck() {
    const response = await this.axios.get('/health');
    return response.data;
  }

  async getDatabaseStats() {
    const response = await this.axios.get('/database/stats');
    return response.data;
  }

  async proposeCharacter(excludeChars = []) {
    const params = { session: this.sessionId };
    if (excludeChars.length > 0) {
      params.exclude = excludeChars.join(',');
    }
    
    const response = await this.axios.get('/propose', { params });
    return response.data;
  }

  async addFilter(characterNumber, value) {
    const response = await this.axios.post('/filter', {
      session: this.sessionId,
      character_number: characterNumber,
      value: value
    });
    return response.data;
  }

  async getState() {
    const response = await this.axios.get('/state', {
      params: { session: this.sessionId }
    });
    return response.data;
  }

  async resetState() {
    const response = await this.axios.delete('/state', {
      params: { session: this.sessionId }
    });
    return response.data;
  }

  async undoLastFilter() {
    const response = await this.axios.post('/undo', {
      session: this.sessionId
    });
    return response.data;
  }

  async getCharacterValues(characterNumber) {
    const response = await this.axios.get(`/character/${characterNumber}/values`, {
      params: { session: this.sessionId }
    });
    return response.data;
  }

  async getCharacterInfo(characterNumber) {
    const response = await this.axios.get(`/character/${characterNumber}/info`);
    return response.data;
  }

  async getItems() {
    const response = await this.axios.get('/items', {
      params: { session: this.sessionId }
    });
    return response.data;
  }

  async runAutoWorkflow(maxSteps = 10) {
    const response = await this.axios.post('/workflow/auto', {
      session: this.sessionId,
      max_steps: maxSteps
    });
    return response.data;
  }

  // Helper method to clean up formatting
  cleanDescription(description) {
    if (typeof description !== 'string') return description;
    
    return description
      .replace(/\\i\{\}/g, '')  // Remove italic start
      .replace(/\\i0\{\}/g, '') // Remove italic end
      .replace(/\\b\{\}/g, '')  // Remove bold start
      .replace(/\\b0\{\}/g, '') // Remove bold end
      .replace(/<</g, '(')      // Replace << with (
      .replace(/>>/g, ')')      // Replace >> with )
      .replace(/</g, '')        // Remove < 
      .replace(/>/g, '')        // Remove >
      .trim();
  }
}

export default DeltaAPI;