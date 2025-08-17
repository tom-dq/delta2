import React, { useState, useEffect } from 'react';
import styled from 'styled-components';

const ProposalContainer = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
`;

const CharacterInfo = styled.div`
  background: #e8f4fd;
  border: 1px solid #bee5eb;
  border-radius: 6px;
  padding: 15px;
  margin-bottom: 20px;
`;

const CharacterTitle = styled.h4`
  color: #0c5460;
  margin: 0 0 10px 0;
  font-size: 1.1rem;
`;

const CharacterDetails = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 10px;
  font-size: 0.9rem;
  color: #495057;
`;

const DetailItem = styled.div`
  strong {
    color: #212529;
  }
`;

const ValuesContainer = styled.div`
  margin-top: 20px;
`;

const ValuesList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 300px;
  overflow-y: auto;
`;

const ValueButton = styled.button`
  background: ${props => props.selected ? '#007bff' : 'white'};
  color: ${props => props.selected ? 'white' : '#495057'};
  border: 1px solid ${props => props.selected ? '#007bff' : '#dee2e6'};
  border-radius: 6px;
  padding: 12px 15px;
  text-align: left;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  justify-content: space-between;
  align-items: center;

  &:hover {
    background: ${props => props.selected ? '#0056b3' : '#f8f9fa'};
    border-color: ${props => props.selected ? '#0056b3' : '#adb5bd'};
  }

  &:disabled {
    background: #f8f9fa;
    color: #6c757d;
    cursor: not-allowed;
    border-color: #dee2e6;
  }
`;

const ValueDescription = styled.div`
  font-weight: 500;
  margin-bottom: 4px;
`;

const ValueMeta = styled.div`
  font-size: 0.8rem;
  opacity: 0.8;
`;

const ItemCount = styled.span`
  background: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
  margin-left: 10px;
`;

const ActionButtons = styled.div`
  display: flex;
  gap: 10px;
  margin-top: 15px;
`;

const Button = styled.button`
  background: ${props => props.variant === 'primary' ? '#28a745' : '#6c757d'};
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;

  &:hover {
    background: ${props => props.variant === 'primary' ? '#218838' : '#545b62'};
  }

  &:disabled {
    background: #6c757d;
    cursor: not-allowed;
    opacity: 0.6;
  }
`;

const CharacterProposal = ({ proposal, onSelectValue, api, loading }) => {
  const [selectedValue, setSelectedValue] = useState(null);
  const [values, setValues] = useState([]);
  const [loadingValues, setLoadingValues] = useState(false);

  useEffect(() => {
    if (proposal?.status === 'success' && proposal.character) {
      setValues(proposal.possible_values || []);
      setSelectedValue(null);
    }
  }, [proposal]);

  const handleValueSelect = (value) => {
    setSelectedValue(value);
  };

  const handleConfirmSelection = () => {
    if (selectedValue && onSelectValue) {
      onSelectValue(proposal.character.number, selectedValue.value);
      setSelectedValue(null);
    }
  };

  const handleGetMoreValues = async () => {
    if (!proposal?.character?.number) return;
    
    try {
      setLoadingValues(true);
      const response = await api.getCharacterValues(proposal.character.number);
      if (response.status === 'success') {
        setValues(response.values);
      }
    } catch (error) {
      console.error('Failed to get character values:', error);
    } finally {
      setLoadingValues(false);
    }
  };

  if (!proposal) {
    return (
      <ProposalContainer>
        <div style={{ textAlign: 'center', color: '#6c757d', padding: '40px 20px' }}>
          <h4>🎯 Identification Complete</h4>
          <p>No more characters needed for discrimination</p>
        </div>
      </ProposalContainer>
    );
  }

  if (proposal.status !== 'success') {
    return (
      <ProposalContainer>
        <div style={{ textAlign: 'center', color: '#dc3545', padding: '20px' }}>
          <h4>⚠️ {proposal.message}</h4>
        </div>
      </ProposalContainer>
    );
  }

  const character = proposal.character;

  return (
    <ProposalContainer>
      <h3 style={{ marginBottom: '20px', color: '#2c3e50' }}>
        🎯 Most Selective Character
      </h3>

      <CharacterInfo>
        <CharacterTitle>
          Character {character.number}: {api.cleanDescription(character.description)}
        </CharacterTitle>
        
        <CharacterDetails>
          <DetailItem>
            <strong>Type:</strong> {character.type}
          </DetailItem>
          <DetailItem>
            <strong>Distinct Values:</strong> {character.distinct_values}
          </DetailItem>
          <DetailItem>
            <strong>Selectivity:</strong> {character.selectivity_score?.toFixed(2)}
          </DetailItem>
          <DetailItem>
            <strong>Remaining Items:</strong> {proposal.remaining_items}
          </DetailItem>
        </CharacterDetails>
      </CharacterInfo>

      <ValuesContainer>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
          <h4 style={{ margin: 0, color: '#495057' }}>Select a Value:</h4>
          {values.length !== proposal.possible_values?.length && (
            <Button 
              onClick={handleGetMoreValues} 
              disabled={loadingValues}
              variant="secondary"
            >
              {loadingValues ? 'Loading...' : 'Show All Values'}
            </Button>
          )}
        </div>

        <ValuesList>
          {values.map((value, index) => (
            <ValueButton
              key={index}
              selected={selectedValue === value}
              onClick={() => handleValueSelect(value)}
              disabled={loading}
            >
              <div>
                <ValueDescription>
                  {api.cleanDescription(value.description)}
                </ValueDescription>
                <ValueMeta>
                  Value: {typeof value.value === 'string' ? 
                    api.cleanDescription(value.value) : 
                    value.value
                  }
                </ValueMeta>
              </div>
              <ItemCount>
                {value.item_count} taxa
              </ItemCount>
            </ValueButton>
          ))}
        </ValuesList>

        <ActionButtons>
          <Button
            variant="primary"
            onClick={handleConfirmSelection}
            disabled={!selectedValue || loading}
          >
            {loading ? 'Applying Filter...' : 'Apply Filter'}
          </Button>
          
          {selectedValue && (
            <Button onClick={() => setSelectedValue(null)}>
              Clear Selection
            </Button>
          )}
        </ActionButtons>
      </ValuesContainer>
    </ProposalContainer>
  );
};

export default CharacterProposal;