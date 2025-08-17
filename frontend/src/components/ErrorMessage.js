import React from 'react';
import styled from 'styled-components';

const ErrorContainer = styled.div`
  background: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
  border-radius: 6px;
  padding: 15px 20px;
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  box-shadow: 0 2px 10px rgba(220, 53, 69, 0.1);
`;

const ErrorContent = styled.div`
  flex: 1;
`;

const ErrorTitle = styled.h4`
  margin: 0 0 8px 0;
  font-size: 1rem;
  display: flex;
  align-items: center;
  gap: 8px;
`;

const ErrorText = styled.p`
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.4;
`;

const CloseButton = styled.button`
  background: none;
  border: none;
  color: #721c24;
  font-size: 20px;
  cursor: pointer;
  padding: 0;
  margin-left: 15px;
  line-height: 1;
  opacity: 0.7;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
`;

const ErrorMessage = ({ message, onClose }) => {
  return (
    <ErrorContainer>
      <ErrorContent>
        <ErrorTitle>
          ⚠️ Error
        </ErrorTitle>
        <ErrorText>{message}</ErrorText>
      </ErrorContent>
      
      {onClose && (
        <CloseButton onClick={onClose} title="Dismiss error">
          ×
        </CloseButton>
      )}
    </ErrorContainer>
  );
};

export default ErrorMessage;