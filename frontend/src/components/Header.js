import React from 'react';
import styled from 'styled-components';

const HeaderContainer = styled.header`
  background: white;
  border-radius: 10px;
  padding: 30px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  text-align: center;
  margin-bottom: 30px;
`;

const Title = styled.h1`
  color: #2c3e50;
  font-size: 2.5rem;
  margin-bottom: 10px;
  font-weight: 700;
`;

const Subtitle = styled.p`
  color: #7f8c8d;
  font-size: 1.2rem;
  margin: 0;
`;

const Header = () => {
  return (
    <HeaderContainer>
      <Title>🔬 DELTA</Title>
      <Subtitle>Interactive Taxonomic Identification System</Subtitle>
    </HeaderContainer>
  );
};

export default Header;