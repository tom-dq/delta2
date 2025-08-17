import React, { useState, useEffect } from 'react';
import styled from 'styled-components';
import DeltaAPI from './services/api';
import Header from './components/Header';
import DatabaseStats from './components/DatabaseStats';
import CharacterProposal from './components/CharacterProposal';
import FilterDisplay from './components/FilterDisplay';
import ItemResults from './components/ItemResults';
import Controls from './components/Controls';
import LoadingSpinner from './components/LoadingSpinner';
import ErrorMessage from './components/ErrorMessage';

const AppContainer = styled.div`
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
`;

const MainContent = styled.div`
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
`;

const Grid = styled.div`
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
  }
`;

const FullWidth = styled.div`
  grid-column: 1 / -1;
`;

function App() {
  const [api] = useState(() => new DeltaAPI());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [dbStats, setDbStats] = useState(null);
  const [currentState, setCurrentState] = useState(null);
  const [proposal, setProposal] = useState(null);
  const [items, setItems] = useState([]);

  useEffect(() => {
    initializeApp();
  }, []);

  const initializeApp = async () => {
    try {
      setLoading(true);
      setError(null);

      // Check API health
      await api.healthCheck();

      // Get database stats
      const stats = await api.getDatabaseStats();
      setDbStats(stats);

      // Reset state and get initial data
      await refreshData();

    } catch (err) {
      setError(`Failed to initialize app: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const refreshData = async () => {
    try {
      // Get current state
      const state = await api.getState();
      setCurrentState(state);

      // Get items
      const itemsData = await api.getItems();
      setItems(itemsData.items || []);

      // Get character proposal if items > 1
      if (itemsData.total_count > 1) {
        const proposalData = await api.proposeCharacter();
        setProposal(proposalData);
      } else {
        setProposal(null);
      }

    } catch (err) {
      setError(`Failed to refresh data: ${err.message}`);
    }
  };

  const handleAddFilter = async (characterNumber, value) => {
    try {
      setLoading(true);
      await api.addFilter(characterNumber, value);
      await refreshData();
    } catch (err) {
      setError(`Failed to add filter: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUndo = async () => {
    try {
      setLoading(true);
      await api.undoLastFilter();
      await refreshData();
    } catch (err) {
      setError(`Failed to undo: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    try {
      setLoading(true);
      await api.resetState();
      await refreshData();
    } catch (err) {
      setError(`Failed to reset: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleAutoWorkflow = async () => {
    try {
      setLoading(true);
      await api.runAutoWorkflow();
      await refreshData();
    } catch (err) {
      setError(`Failed to run auto workflow: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !currentState) {
    return (
      <AppContainer>
        <MainContent>
          <LoadingSpinner message="Initializing DELTA system..." />
        </MainContent>
      </AppContainer>
    );
  }

  return (
    <AppContainer>
      <MainContent>
        <Header />
        
        {error && <ErrorMessage message={error} onClose={() => setError(null)} />}
        
        {dbStats && <DatabaseStats stats={dbStats} />}
        
        <Controls
          onUndo={handleUndo}
          onReset={handleReset}
          onAutoWorkflow={handleAutoWorkflow}
          canUndo={currentState?.filters?.length > 0}
          loading={loading}
        />

        <Grid>
          <div>
            {proposal && (
              <CharacterProposal
                proposal={proposal}
                onSelectValue={handleAddFilter}
                api={api}
                loading={loading}
              />
            )}
          </div>
          
          <div>
            <FilterDisplay
              filters={currentState?.filters || []}
              remainingItems={currentState?.remaining_count || 0}
            />
            
            <ItemResults
              items={items}
              totalCount={currentState?.remaining_count || 0}
            />
          </div>
        </Grid>
      </MainContent>
    </AppContainer>
  );
}

export default App;