import React from 'react';
import styled from 'styled-components';

const ControlsContainer = styled.div`
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  margin-bottom: 20px;
`;

const ButtonGroup = styled.div`
  display: flex;
  gap: 15px;
  flex-wrap: wrap;
  align-items: center;
`;

const Button = styled.button`
  background: ${props => {
    if (props.variant === 'danger') return '#dc3545';
    if (props.variant === 'warning') return '#ffc107';
    if (props.variant === 'success') return '#28a745';
    return '#6c757d';
  }};
  color: ${props => props.variant === 'warning' ? '#212529' : 'white'};
  border: none;
  padding: 12px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 8px;

  &:hover {
    background: ${props => {
      if (props.variant === 'danger') return '#c82333';
      if (props.variant === 'warning') return '#e0a800';
      if (props.variant === 'success') return '#218838';
      return '#545b62';
    }};
    transform: translateY(-1px);
  }

  &:disabled {
    background: #6c757d;
    cursor: not-allowed;
    opacity: 0.6;
    transform: none;
  }

  &:active {
    transform: translateY(0);
  }
`;

const Divider = styled.div`
  width: 1px;
  height: 30px;
  background: #dee2e6;
  margin: 0 10px;
`;

const Description = styled.p`
  margin: 15px 0 0 0;
  color: #6c757d;
  font-size: 0.9rem;
  line-height: 1.4;
`;

const Controls = ({ onUndo, onReset, onAutoWorkflow, canUndo, loading }) => {
  return (
    <ControlsContainer>
      <ButtonGroup>
        <Button
          onClick={onUndo}
          disabled={!canUndo || loading}
          title="Remove the last applied filter"
        >
          ↶ Undo Last Filter
        </Button>

        <Button
          variant="danger"
          onClick={onReset}
          disabled={loading}
          title="Clear all filters and start over"
        >
          🔄 Reset All
        </Button>

        <Divider />

        <Button
          variant="success"
          onClick={onAutoWorkflow}
          disabled={loading}
          title="Automatically build identification key"
        >
          🤖 Auto Identify
        </Button>

        {loading && (
          <>
            <Divider />
            <div style={{ 
              color: '#007bff', 
              fontWeight: '500',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <div style={{
                width: '16px',
                height: '16px',
                border: '2px solid #f3f3f3',
                borderTop: '2px solid #007bff',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }} />
              Processing...
            </div>
          </>
        )}
      </ButtonGroup>

      <Description>
        <strong>Instructions:</strong> Use the character proposal above to select values and narrow down taxa. 
        The system automatically suggests the most discriminating characters first. 
        Use "Auto Identify" for an automated workflow, or build your key step by step.
      </Description>

      <style jsx>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </ControlsContainer>
  );
};

export default Controls;