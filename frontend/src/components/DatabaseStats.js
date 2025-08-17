import React from 'react';
import styled from 'styled-components';

const StatsContainer = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
`;

const StatsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 20px;
`;

const StatItem = styled.div`
  text-align: center;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
`;

const StatNumber = styled.div`
  font-size: 2rem;
  font-weight: bold;
  color: #007bff;
  margin-bottom: 5px;
`;

const StatLabel = styled.div`
  color: #6c757d;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
`;

const TypesContainer = styled.div`
  margin-top: 15px;
  text-align: left;
`;

const TypesList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 10px;
`;

const TypeBadge = styled.span`
  background: #e9ecef;
  color: #495057;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 0.8rem;
  font-weight: 500;
`;

const DatabaseStats = ({ stats }) => {
  const typeLabels = {
    'TE': 'Text',
    'IN': 'Integer',
    'RN': 'Real',
    'UM': 'Unordered Multistate',
    'OM': 'Ordered Multistate'
  };

  return (
    <StatsContainer>
      <h3 style={{ marginBottom: '20px', color: '#2c3e50' }}>Database Overview</h3>
      
      <StatsGrid>
        <StatItem>
          <StatNumber>{stats.characters}</StatNumber>
          <StatLabel>Characters</StatLabel>
        </StatItem>
        
        <StatItem>
          <StatNumber>{stats.items}</StatNumber>
          <StatLabel>Taxa</StatLabel>
        </StatItem>
        
        <StatItem>
          <StatNumber>{Object.keys(stats.character_types).length}</StatNumber>
          <StatLabel>Character Types</StatLabel>
        </StatItem>
      </StatsGrid>

      <TypesContainer>
        <h4 style={{ color: '#495057', marginBottom: '10px' }}>Character Types:</h4>
        <TypesList>
          {Object.entries(stats.character_types).map(([type, count]) => (
            <TypeBadge key={type}>
              {typeLabels[type] || type}: {count}
            </TypeBadge>
          ))}
        </TypesList>
      </TypesContainer>
    </StatsContainer>
  );
};

export default DatabaseStats;