import React from 'react';
import { Box, Typography } from '@mui/material';

// Constants derived from Figma colors and coordinates
const DARK_GREEN = 'rgba(0, 65, 0, 1)'; // logi patch desigbn111 color
const PRIMARY_BLUE = 'rgba(8, 62, 222, 1)'; // Button background

export const UserProfile = () => {

  const FRAME_WIDTH = 1512;
  const FRAME_HEIGHT = 982;
  
  // Component 1: The large black rectangle (ID 66:2)
  // Position relative to parent frame 1:4 (W: 441, H: 669, X: 184, Y: 245)
  const BlackBox = (
    <Box
      sx={{
        position: 'absolute',
        top: 245,
        left: 184,
        width: 441,
        height: 669,
        backgroundColor: '#000000',
      }}
    />
  );

  // Component 2: The Blue Button container (Frame 2: ID 47:3)
  // Position relative to parent frame 1:4 (W: 217, H: 272, X: 989, Y: 561)
  const CustomButton = (
    <Box
      sx={{
        position: 'absolute',
        top: 561,
        left: 989,
        width: 217,
        height: 272,
        backgroundColor: PRIMARY_BLUE,
        borderRadius: '12px',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        boxSizing: 'border-box',
      }}
    >
      {/* Button Text (ID: 47:2) */}
      <Typography
        sx={{
          fontFamily: 'Geist, sans-serif',
          fontWeight: 400,
          fontSize: 36,
          lineHeight: '46.8px', 
          color: '#FFFFFF',
        }}
      >
        Button
      </Typography>
    </Box>
  );
  
  // Component 3: The Title text (ID: 1:5)
  // Position relative to parent frame 1:4 (X: 51, Y: 54)
  const TitleText = (
      <Typography
        variant="h1" 
        sx={{
          position: 'absolute',
          top: 54,
          left: 51,
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 128,
          letterSpacing: '-8.96px',
          lineHeight: '154.91px', 
          color: DARK_GREEN,
          whiteSpace: 'nowrap',
        }}
      >
        logi patch desigbn111
      </Typography>
  );


  return (
    <Box
      sx={{
        width: FRAME_WIDTH,
        height: FRAME_HEIGHT,
        backgroundColor: '#FFFFFF', // Frame background
        position: 'relative', 
        overflow: 'hidden', 
      }}
    >
      {TitleText}
      {BlackBox}
      {CustomButton}
    </Box>
  );
};