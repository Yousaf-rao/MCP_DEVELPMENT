import React from 'react';
import { Box, Typography } from '@mui/material';

// Function to safely calculate colors from Figma float format
const figmaColorToCss = (color) => {
    const r = Math.round(color.r * 255);
    const g = Math.round(color.g * 255);
    const b = Math.round(color.b * 255);
    const a = color.a !== undefined ? color.a : 1.0;

    if (a >= 1.0) {
        // Convert opaque colors to Hex
        return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1).padStart(6, '0').toUpperCase()}`;
    }
    return `rgba(${r}, ${g}, ${b}, ${a})`;
};

export const UserProfile = () => {

    // 1. logi patch desigbn111 (ID: 1:5)
    const TitleStyle = {
        color: figmaColorToCss({ r: 0.0, g: 0.25480762124061584, b: 0.0, a: 0.8299999833106995 }), // rgba(0, 65, 0, 0.83)
        fontSize: '128px',
        fontWeight: 600,
        fontFamily: 'Inter, sans-serif',
        letterSpacing: '-8.96px',
        lineHeight: '155px',
    };

    // 2. Click (ID: 4:2) inside Frame 1 (ID: 4:3)
    const ClickBoxStyle = {
        boxShadow: '0px 4px 4px rgba(0, 0, 0, 0.25)',
        p: '10px',
        width: 242,
        height: 160,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
    };
    const ClickTextStyle = {
        color: figmaColorToCss({ r: 0.538461446762085, g: 0.012080918997526169, b: 0.012080918997526169, a: 1.0 }), // #890303
        fontFamily: '"Irish Grover", cursive',
        fontSize: '36px',
        lineHeight: '44px',
    };

    // 3. Button (ID: 47:2) inside Frame 2 (ID: 47:3)
    const ButtonFrameStyle = {
        bgcolor: figmaColorToCss({ r: 0.03171851113438606, g: 0.24147336184978485, b: 0.8707379102706909, a: 1.0 }), // #083EDE (Blue)
        borderRadius: '12px',
        width: 217,
        height: 272,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
    };

    const ButtonTextStyle = {
        color: '#FFFFFF',
        fontFamily: 'Geist, sans-serif',
        fontSize: '36px',
        fontWeight: 400,
        lineHeight: '47px',
    };

    // 4. Rectangle 2 (ID: 142:3) - Red Bar
    const ExtensionRectangleStyle = {
        bgcolor: figmaColorToCss({ r: 0.4503205418586731, g: 0.07794009149074554, b: 0.07794009149074554, a: 1.0 }), // #731414 (Dark Red)
        width: 726,
        height: 102,
        border: '1px solid #1E1E1E',
        boxShadow: '0px 4px 4px rgba(65, 0, 0, 0.8)',
    };

    // 5. Retro Text (ID: 142:5)
    const RetroTextStyle = {
        color: figmaColorToCss({ r: 0.044978633522987366, g: 0.0, b: 0.6746794581413269, a: 1.0 }), // #0B00AC
        fontFamily: 'Inter, serif',
        fontStyle: 'italic',
        fontWeight: 900,
        fontSize: '64px',
        lineHeight: '77px',
    };
    
    // Main Frame dimensions
    const frameWidth = 1512;
    const frameHeight = 982;

    // Absolute offsets calculated relative to main Frame 1:4 (Top-Left corner at -2705, -3501)

    return (
        <Box
            sx={{
                width: frameWidth,
                height: frameHeight,
                bgcolor: '#FFFFFF',
                position: 'relative',
                overflow: 'hidden',
            }}
        >
            {/* 1. logi patch desigbn111 (Offset X=51, Y=54) */}
            <Typography component="h1" sx={{
                ...TitleStyle,
                position: 'absolute',
                top: 54,
                left: 51,
            }}>
                 logi patch desigbn111
            </Typography>

            {/* 2. Click Frame 1 (Offset X=372, Y=242) */}
            <Box sx={{
                ...ClickBoxStyle,
                position: 'absolute',
                top: 242,
                left: 372,
            }}>
                <Typography component="span" sx={ClickTextStyle}>Click</Typography>
            </Box>

            {/* 4. Retro Text (Offset X=894, Y=411) */}
            <Typography component="h3" sx={{
                ...RetroTextStyle,
                position: 'absolute',
                top: 411,
                left: 894,
            }}>
                Retro
            </Typography>
            
            {/* 3. Button Group Container (Anchored at Frame 2 start: X=225, Y=491) */}
            <Box sx={{
                position: 'absolute',
                top: 491,
                left: 225,
                // Define a large enough area to contain both blue box and red bar
                width: 217 + 726, 
                height: 272,
            }}>
                {/* Frame 2: Blue Button Box (217x272) */}
                <Box sx={{
                    ...ButtonFrameStyle,
                    position: 'relative',
                    zIndex: 1, 
                }}>
                    <Typography component="span" sx={ButtonTextStyle}>Button</Typography>
                </Box>

                {/* Rectangle 2: Red Bar (726x102) 
                    Offset relative to Frame 2 start: X=202, Y=121
                */}
                <Box sx={{
                    ...ExtensionRectangleStyle,
                    position: 'absolute',
                    left: 202,
                    top: 121,
                    zIndex: 0,
                }} />
            </Box>
        </Box>
    );
};